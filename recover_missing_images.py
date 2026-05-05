#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import difflib
import io
import json
import re
import time
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any

import requests
from PIL import Image

import sync_images as si


PAREN_RE = re.compile(r"（[^）]*）|\([^)]*\)")
SPACE_RE = re.compile(r"[ \t\u3000]+")
PUNCT_RE = re.compile(r"[・!！?？\s\u3000]+")


def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "").strip())


def strip_paren(s: str) -> str:
    return PAREN_RE.sub("", nfkc(s)).strip()


def norm_name(s: str) -> str:
    t = strip_paren(s)
    t = PUNCT_RE.sub("", t)
    return t


def is_valid_face_png_url(url: str) -> bool:
    u = (url or "").strip().lower().split("?", 1)[0]
    return "/assets/faces/" in u and u.endswith(".png")


def load_faces_json(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"{path}: faces JSON は配列である必要があります")
    rows: list[dict[str, Any]] = []
    for i, row in enumerate(raw):
        if not isinstance(row, dict):
            continue
        nm = str(row.get("name") or "").strip()
        url = str(row.get("url") or "").strip()
        if not nm or not url:
            continue
        if not is_valid_face_png_url(url):
            continue
        rows.append({"name": nm, "url": url})
    return rows


def download_to_webp(session: requests.Session, url: str, out_path: Path) -> None:
    r = session.get(url, timeout=90)
    r.raise_for_status()
    im = Image.open(io.BytesIO(r.content))
    im = im.convert("RGBA")
    im = im.resize((400, 400), Image.Resampling.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    im.save(out_path, format="WEBP", quality=80, method=6)


def build_name_to_url_map(extracted_dir: Path, renames_norm_to_canon: dict[str, str]) -> dict[str, str]:
    """
    正規化名 -> url
    - name_corrections の renames も加味（normalize_key を使う）
    """
    mp: dict[str, str] = {}
    for p in sorted(extracted_dir.glob("*.json*")):
        # .json.json もありえるので、json.loads 可能なものだけ読む
        try:
            faces = load_faces_json(p)
        except Exception:
            continue
        for row in faces:
            nm = str(row["name"])
            url = str(row["url"])
            keys = []
            n0 = norm_name(nm)
            if n0:
                keys.append(n0)
            # renames: まず strip_paren してから normalize_key で引く
            rk = si.normalize_key(strip_paren(nm))
            canon = renames_norm_to_canon.get(rk)
            if canon:
                n1 = norm_name(canon)
                if n1:
                    keys.append(n1)
            for k in keys:
                # 先勝ち（複数アークが同名を持つ場合、最初に見つかったURLを使う）
                mp.setdefault(k, url)
    return mp


def candidates_for_char_name(ch: dict[str, Any], renames_norm_to_canon: dict[str, str]) -> list[str]:
    """
    characters側の照合候補キー（正規化済）
    """
    out: list[str] = []
    for key in ("name", "alias", "reading"):
        v = ch.get(key)
        if not isinstance(v, str) or not v.strip():
            continue
        out.append(v.strip())
        if key == "alias":
            for part in re.split(r"[,、／/]", v):
                p = part.strip()
                if p:
                    out.append(p)
    uniq: list[str] = []
    seen = set()
    for s in out:
        k = norm_name(s)
        if k and k not in seen:
            seen.add(k)
            uniq.append(k)
        rk = si.normalize_key(strip_paren(s))
        canon = renames_norm_to_canon.get(rk)
        if canon:
            k2 = norm_name(canon)
            if k2 and k2 not in seen:
                seen.add(k2)
                uniq.append(k2)
    return uniq


def main() -> int:
    ap = argparse.ArgumentParser(description="不足サムネを extracted データから復元")
    ap.add_argument("--characters", default="src/data/characters.json")
    ap.add_argument("--extracted-dir", default="src/data/extracted")
    ap.add_argument("--thumb-dir", default="public/images/thumbnails")
    ap.add_argument("--sleep", type=float, default=0.15)
    ap.add_argument("--hint-limit", type=int, default=80)
    ap.add_argument("--hint-threshold", type=float, default=0.86)
    args = ap.parse_args()

    chars_path = Path(args.characters)
    extracted_dir = Path(args.extracted_dir)
    thumb_dir = Path(args.thumb_dir)

    chars = json.loads(chars_path.read_text(encoding="utf-8"))
    if not isinstance(chars, list):
        raise SystemExit("characters.json は配列である必要があります")

    renames = si.load_renames(si.CORRECTIONS_PATH)
    name_to_url = build_name_to_url_map(extracted_dir, renames)

    missing: list[dict[str, Any]] = []
    for ch in chars:
        if not isinstance(ch, dict):
            continue
        try:
            cid = int(ch.get("id"))
        except Exception:
            continue
        out_p = thumb_dir / f"{cid}.webp"
        if not out_p.exists():
            missing.append(ch)

    before_missing = len(missing)

    session = requests.Session()
    session.headers.update({"User-Agent": si.CHROME_UA})

    downloaded_ok = 0
    downloaded_fail = 0
    still_missing_ids: set[int] = set()

    # optional hints
    hint_rows: list[dict[str, Any]] = []
    dict_keys = list(name_to_url.keys())

    for ch in missing:
        cid = int(ch["id"])
        out_p = thumb_dir / f"{cid}.webp"
        if out_p.exists():
            continue

        keys = candidates_for_char_name(ch, renames)
        picked_url = None
        picked_key = None
        for k in keys:
            u = name_to_url.get(k)
            if u:
                picked_url = u
                picked_key = k
                break

        if picked_url:
            try:
                si.remove_stale_images(cid)
                download_to_webp(session, picked_url, out_p)
                downloaded_ok += 1
            except Exception as e:
                downloaded_fail += 1
                still_missing_ids.add(cid)
            time.sleep(max(0.0, args.sleep))
        else:
            still_missing_ids.add(cid)
            # hint: best close match (difflib)
            if dict_keys:
                q = norm_name(str(ch.get("name") or ""))
                if q:
                    close = difflib.get_close_matches(q, dict_keys, n=1, cutoff=args.hint_threshold)
                    if close:
                        best = close[0]
                        hint_rows.append(
                            {
                                "id": cid,
                                "name": str(ch.get("name") or ""),
                                "hint_key": best,
                                "hint_url": name_to_url.get(best, ""),
                            }
                        )
                        if len(hint_rows) >= args.hint_limit:
                            dict_keys = []  # stop hints

    after_missing = len(still_missing_ids)

    # write hints csv (optional)
    if hint_rows:
        hint_path = Path("missing_images_hints.csv")
        with hint_path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["id", "name", "hint_key", "hint_url"])
            w.writeheader()
            w.writerows(hint_rows)
        print(f"Wrote {hint_path} ({len(hint_rows)} hints)")

    print(f"開始前の画像不足キャラ数: {before_missing}")
    print(f"今回新しく設定（ダウンロード成功）した画像数: {downloaded_ok}")
    print(f"ダウンロード失敗数: {downloaded_fail}")
    print(f"依然として画像が設定されていない残りのキャラ数: {after_missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

