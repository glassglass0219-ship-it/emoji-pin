#!/usr/bin/env python3
"""
最適化版: [{name,url}] JSON と characters.json / thumbnails を同期する（v3）

改善点:
- 名前照合の強化:
  - 記号（・、！、？、スペース等）除去
  - 括弧内補足の除去（例: コビー（海軍大佐）→コビー）
  - それでも見つからない場合、部分一致・簡易Fuzzyで候補探索
- arcs 追加は重複なし
- 画像処理:
  - thumbnails/{id}.webp が無いときのみDL・変換
  - 失敗はスキップし、最後に失敗リストを出す
  - WebP / 400x400 / quality=80
"""

from __future__ import annotations

import argparse
import difflib
import io
import json
import os
import re
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests
from PIL import Image

import sync_images as si

ROOT = si.ROOT
CHAR_PATH = si.CHAR_PATH
CORRECTIONS_PATH = si.CORRECTIONS_PATH
PUBLIC_THUMB = si.PUBLIC_THUMB

STRICT_KEYWORDS = [
    "ベガパンク",
    "セラフィム",
    "パシフィスタ",
    "S-ホーク",
    "S-スネーク",
    "S-シャーク",
    "S-ベア",
]


PAREN_RE = re.compile(r"（[^）]*）|\([^)]*\)")
SPACE_RE = re.compile(r"[ \t\u3000]+")
PUNCT_RE = re.compile(r"[・!！?？\s\u3000]+")


def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "").strip())


def strip_paren(s: str) -> str:
    return PAREN_RE.sub("", nfkc(s)).strip()


def norm_name(s: str) -> str:
    """
    照合用の正規化:
    - NFKC
    - 括弧内補足除去
    - 記号（・、！、？、空白）除去
    """
    t = strip_paren(s)
    t = PUNCT_RE.sub("", t)
    return t


def is_strict_variant_name(name: str) -> bool:
    s = nfkc(name)
    return any(k in s for k in STRICT_KEYWORDS)


def find_exact_name(chars: list[dict], name: str) -> dict | None:
    target = nfkc(name)
    if not target:
        return None
    for ch in chars:
        if not isinstance(ch, dict):
            continue
        if nfkc(str(ch.get("name") or "")) == target:
            return ch
    return None


def is_valid_face_png_url(url: str) -> bool:
    u = (url or "").strip().lower().split("?", 1)[0]
    return "/assets/faces/" in u and u.endswith(".png")


def load_faces_json(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, list):
        raise ValueError("faces JSON は配列である必要があります")
    rows = []
    for i, row in enumerate(raw):
        if not isinstance(row, dict):
            continue
        nm = str(row.get("name") or "").strip()
        url = str(row.get("url") or "").strip()
        if not nm or not url:
            raise ValueError(f"行 {i}: name と url が必須です")
        if not is_valid_face_png_url(url):
            print(f"[SKIP 非顔PNG] 行 {i} {nm!r} … {url[:72]}")
            continue
        rows.append({"name": nm, "url": url})
    return rows


def max_char_id(chars: list[dict]) -> int:
    best = 0
    for c in chars:
        if not isinstance(c, dict):
            continue
        cid = c.get("id")
        if cid is None:
            continue
        s = str(cid).strip()
        if s.isdigit():
            best = max(best, int(s))
    return best


def load_merges(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    mp = data.get("merges") or {}
    out: dict[str, str] = {}
    for k, v in mp.items():
        if not isinstance(k, str) or not isinstance(v, str):
            continue
        nk = nfkc(k)
        nv = nfkc(v)
        if nk:
            out[nk] = nv
    return out


def resolve_merge_display(name: str, merges_exact: dict[str, str]) -> str:
    n = nfkc(name)
    return merges_exact.get(n, n)


def collect_candidate_strings(char: dict) -> list[str]:
    out: list[str] = []
    for key in ("name", "alias", "reading", "en_name"):
        v = char.get(key)
        if not isinstance(v, str):
            continue
        v = v.strip()
        if not v:
            continue
        out.append(v)
        if key == "alias":
            for part in re.split(r"[,、／/]", v):
                p = part.strip()
                if p:
                    out.append(p)
    # uniq preserving order
    seen = set()
    uniq: list[str] = []
    for s in out:
        k = nfkc(s)
        if not k or k in seen:
            continue
        seen.add(k)
        uniq.append(s)
    return uniq


@dataclass(frozen=True)
class Match:
    score: float
    char: dict
    reason: str


def best_match_for_name(chars: list[dict], name: str, renames: dict[str, str]) -> Match | None:
    """
    Fuzzy matching:
    - 正規化（括弧除去+記号除去）一致: score 100
    - 片方が片方を含む（>=3）: score 92
    - difflib ratio: score 0-100
    """
    disp = nfkc(name)
    base = norm_name(disp)
    if not base:
        return None

    # 厳格対象は Exact のみ（部分一致・Fuzzyでの吸収を禁止）
    if is_strict_variant_name(disp):
        for ch in chars:
            if not isinstance(ch, dict):
                continue
            for cand in collect_candidate_strings(ch):
                if norm_name(cand) == base:
                    return Match(100.0, ch, f"STRICT exact normalized: {cand!r}")
        return None

    # corrections renames: normalize_key は sync_images のルール（中点/空白など）
    # v3 は括弧除去もするので、両方試す
    base_rename = renames.get(si.normalize_key(strip_paren(disp)), "")
    base_rename_norm = norm_name(base_rename) if base_rename else ""

    best: Match | None = None

    for ch in chars:
        if not isinstance(ch, dict):
            continue
        for cand in collect_candidate_strings(ch):
            cn = norm_name(cand)
            if not cn:
                continue
            # exact normalized
            if cn == base or (base_rename_norm and cn == base_rename_norm):
                m = Match(100.0, ch, f"normalized exact: {cand!r}")
            else:
                # substring
                shorter, longer = (base, cn) if len(base) <= len(cn) else (cn, base)
                if len(shorter) >= 3 and shorter in longer:
                    m = Match(92.0 + min(7.0, len(shorter) / 10.0), ch, f"substring: {cand!r}")
                else:
                    r = difflib.SequenceMatcher(None, base, cn).ratio()
                    # ratio を 0-100 に
                    m = Match(r * 100.0, ch, f"fuzzy({r:.3f}): {cand!r}")

            if best is None or m.score > best.score:
                best = m

    # 閾値: fuzzy のみだと誤爆があるので最低 86
    if best and best.score >= 86.0:
        return best
    return None


def download_to_webp_v3(session: requests.Session, url: str, out_path: Path) -> None:
    r = session.get(url, timeout=90)
    r.raise_for_status()
    im = Image.open(io.BytesIO(r.content))
    im = im.convert("RGBA")
    im = im.resize((400, 400), Image.Resampling.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    im.save(out_path, format="WEBP", quality=80, method=6)


def resolve_source_path(p: Path) -> Path:
    """
    指定パスが無い場合、.json.json などのよくある派生も探す。
    """
    if p.is_absolute():
        base = p
    else:
        base = ROOT / p
    if base.exists():
        return base
    # egghead_wt100_faces.json -> egghead_wt100_faces.json.json
    alt = Path(str(base) + ".json")
    if alt.exists():
        return alt
    raise FileNotFoundError(str(base))


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="WT100 顔 JSON と characters.json / サムネを同期（v3）")
    p.add_argument("--arc-name", required=True)
    p.add_argument(
        "--json-file",
        type=Path,
        default=Path("src/data/extracted/egghead_wt100_faces.json"),
        help="[{name,url}, ...] 形式の JSON ファイル（無ければ .json.json も探索）",
    )
    p.add_argument("--sleep", type=float, default=0.22)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    os.chdir(ROOT)

    arc_name = (args.arc_name or "").strip()
    faces_path = resolve_source_path(args.json_file)

    renames = si.load_renames(CORRECTIONS_PATH)
    merges = load_merges(CORRECTIONS_PATH)
    faces_data = load_faces_json(faces_path)

    with CHAR_PATH.open(encoding="utf-8") as f:
        chars: list[dict] = json.load(f)
    si.ensure_arcs_field(chars)

    session = requests.Session()
    session.headers.update({"User-Agent": si.CHROME_UA})

    next_id = max_char_id(chars)

    updated_existing = 0
    added_new = 0
    downloaded_ok = 0
    downloaded_fail = 0
    failed_downloads: list[dict[str, Any]] = []
    suspicious_new: list[dict[str, Any]] = []

    for row in faces_data:
        display_name = row["name"]
        url = row["url"]
        resolved = resolve_merge_display(display_name, merges)

        strict = is_strict_variant_name(resolved)

        # 1) まず既存の高精度 matcher。ただし strict は完全一致のみ。
        if strict:
            ch = find_exact_name(chars, resolved)
        else:
            ch = si.find_character(chars, resolved, "", renames)

        # 2) 見つからなければ v3 の柔軟マッチ
        m: Match | None = None
        if ch is None:
            m = best_match_for_name(chars, resolved, renames)
            if m is not None:
                ch = m.char

        is_new = False
        if ch is None:
            # 新規。ただし「微妙に違って新規になった」候補を出すため、低めの閾値で再探索
            loose = None
            # loose 探索（閾値 76）
            base = norm_name(resolved)
            best_loose = None
            if base:
                for cand_ch in chars:
                    if not isinstance(cand_ch, dict):
                        continue
                    for cand in collect_candidate_strings(cand_ch):
                        cn = norm_name(cand)
                        if not cn:
                            continue
                        r = difflib.SequenceMatcher(None, base, cn).ratio() * 100.0
                        if best_loose is None or r > best_loose[0]:
                            best_loose = (r, cand_ch, cand)
                if best_loose and best_loose[0] >= 76.0:
                    loose = best_loose

            next_id += 1
            stub = si.new_character_stub(next_id, resolved, "")
            chars.append(stub)
            ch = stub
            is_new = True
            added_new += 1
            print(f"[NEW id={next_id}] {resolved}")

            if loose is not None:
                score, cand_ch, cand_str = loose
                suspicious_new.append(
                    {
                        "new_id": next_id,
                        "new_name": resolved,
                        "candidate_id": int(cand_ch.get("id", 0) or 0),
                        "candidate_name": str(cand_ch.get("name") or ""),
                        "candidate_hit": cand_str,
                        "score": round(score, 2),
                    }
                )
        else:
            updated_existing += 1
            if m is not None:
                print(f"[MATCH v3 {m.score:.1f}] {resolved} -> id={ch.get('id')} ({m.reason})")

        if arc_name:
            si.append_arc_unique(ch, arc_name)

        cid = int(ch["id"])
        out_p = PUBLIC_THUMB / f"{cid}.webp"
        if out_p.exists():
            # 画像があるなら何もしない
            time.sleep(0.0)
        else:
            try:
                si.remove_stale_images(cid)
                download_to_webp_v3(session, url, out_p)
                downloaded_ok += 1
            except Exception as e:
                downloaded_fail += 1
                failed_downloads.append(
                    {
                        "id": cid,
                        "name": str(ch.get("name") or ""),
                        "source_name": resolved,
                        "url": url,
                        "error": repr(e),
                    }
                )
                print(f"[IMG FAIL id={cid}] {resolved} … {repr(e)[:140]}")
            time.sleep(max(0.0, args.sleep))

    chars.sort(key=lambda x: int(str(x.get("id", 0)) or 0))
    with CHAR_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print()
    print(f"ソース: {faces_path} ({len(faces_data)} 件)")
    print(f"照合に成功し、情報を更新した人数: {updated_existing}")
    print(f"新規キャラクターとして登録した人数: {added_new}")
    print(f"画像ダウンロードに成功した数: {downloaded_ok}")
    print(f"画像ダウンロードに失敗した数: {downloaded_fail}")
    if failed_downloads:
        print("失敗リスト:")
        for r in failed_downloads:
            print(f"  - id={r['id']} name={r['name']!r} src={r['source_name']!r}")
    if suspicious_new:
        print("重要: 名前が微妙に違って「新規」に振られてしまった可能性のあるキャラ:")
        for r in suspicious_new:
            print(
                f"  - new id={r['new_id']} {r['new_name']!r}  vs  "
                f"candidate id={r['candidate_id']} {r['candidate_name']!r} "
                f"(hit={r['candidate_hit']!r} score={r['score']})"
            )
    else:
        print("重要: 「新規」誤判定の疑いリスト: なし")
    if arc_name:
        print(f"編タグ適用: 「{arc_name}」")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

