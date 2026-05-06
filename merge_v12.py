#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import re
import unicodedata
from pathlib import Path

import requests
from PIL import Image, ImageOps


CHAR_PATH = Path("src/data/characters.json")
THUMBS_DIR = Path("public/images/thumbnails")

SIZE = 400
WEBP_QUALITY = 82
TIMEOUT_SEC = 30


def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "").strip())


_SPACE_RE = re.compile(r"[ \t\u3000]+")


def norm_name(s: str) -> str:
    t = nfkc(s)
    t = _SPACE_RE.sub("", t)
    t = t.lower()
    for ch in ["・", "･", "“", "”", "〝", "〟", "「", "」", "『", "』", "｢", "｣"]:
        t = t.replace(ch, "")
    return t


def ensure_list(v: object) -> list:
    if isinstance(v, list):
        return v
    if v in (None, ""):
        return []
    return [v]


def uniq_list(seq: list) -> list:
    out = []
    seen = set()
    for x in seq:
        key = json.dumps(x, ensure_ascii=False, sort_keys=True) if isinstance(x, (dict, list)) else str(x)
        if key in seen:
            continue
        seen.add(key)
        out.append(x)
    return out


def merge_appearances(a: object, b: object) -> list:
    al = a if isinstance(a, list) else []
    bl = b if isinstance(b, list) else []
    by_ep: dict[int, dict] = {}
    other = []
    for row in al + bl:
        if isinstance(row, dict) and isinstance(row.get("episode"), int):
            ep = int(row["episode"])
            prev = by_ep.get(ep)
            if not prev or (not prev.get("title") and row.get("title")):
                by_ep[ep] = row
        else:
            other.append(row)
    merged = other + [by_ep[k] for k in sorted(by_ep.keys())]
    return uniq_list(merged)


def merge_value(dst: dict, src: dict, key: str) -> None:
    dv = dst.get(key)
    sv = src.get(key)

    if key == "appearances":
        dst[key] = merge_appearances(dv, sv)
        return

    if key in {"arcs", "abilities", "covers", "coAppearances", "category", "group"}:
        dl = ensure_list(dv)
        sl = ensure_list(sv)
        # flatten string lists, keep non-empty
        merged = []
        for x in dl + sl:
            if isinstance(x, str):
                t = x.strip()
                if t:
                    merged.append(t)
            elif x not in (None, ""):
                merged.append(x)
        dst[key] = uniq_list(merged)
        return

    # scalar/object: keep dst if meaningful, otherwise take src
    if dv in (None, "", []):
        dst[key] = sv


def find_char(chars: list[dict], name: str) -> list[dict]:
    exact = [c for c in chars if isinstance(c, dict) and c.get("name") == name]
    if exact:
        return exact
    key = norm_name(name)
    return [c for c in chars if isinstance(c, dict) and norm_name(str(c.get("name") or "")) == key]


def download_to_webp(url: str) -> bytes:
    r = requests.get(url, timeout=TIMEOUT_SEC)
    r.raise_for_status()
    im = Image.open(io.BytesIO(r.content)).convert("RGBA")
    im = ImageOps.fit(im, (SIZE, SIZE), method=Image.LANCZOS)
    out = io.BytesIO()
    im.save(out, format="WEBP", quality=WEBP_QUALITY, method=6)
    return out.getvalue()


def ensure_thumb(id_: int, url: str) -> None:
    THUMBS_DIR.mkdir(parents=True, exist_ok=True)
    (THUMBS_DIR / f"{id_}.webp").write_bytes(download_to_webp(url))


def merge_pair(chars: list[dict], left_name: str, right_name: str) -> tuple[int, int]:
    left_hits = find_char(chars, left_name)
    right_hits = find_char(chars, right_name)
    if not left_hits or not right_hits:
        raise RuntimeError(f"pair not found: {left_name} / {right_name}")

    # choose smallest id within each side for determinism
    left = min(left_hits, key=lambda c: int(c.get("id", 10**9)))
    right = min(right_hits, key=lambda c: int(c.get("id", 10**9)))

    keep = left if int(left["id"]) <= int(right["id"]) else right
    drop = right if keep is left else left

    keep_id = int(keep["id"])
    drop_id = int(drop["id"])

    # final name is left side of "/"
    keep["name"] = left_name

    # merge all keys from drop into keep
    for k in drop.keys():
        if k == "id":
            continue
        merge_value(keep, drop, k)

    # thumbnail handoff
    keep_path = THUMBS_DIR / f"{keep_id}.webp"
    drop_path = THUMBS_DIR / f"{drop_id}.webp"
    if drop_path.exists() and not keep_path.exists():
        drop_path.rename(keep_path)
    elif drop_path.exists() and keep_path.exists():
        drop_path.unlink()

    # remove drop entry (by object identity)
    chars.remove(drop)
    return keep_id, drop_id


def main() -> int:
    chars = json.loads(CHAR_PATH.read_text(encoding="utf-8"))
    if not isinstance(chars, list):
        raise SystemExit("characters.json must be a list")

    # 1) add/overwrite images
    image_updates = [
        ("チャオ", 884, "https://onepiecewt100-2026.com/assets/faces/0880.png?v=gjdgxu"),
        ("原", 1166, "https://onepiecewt100-2026.com/assets/faces/1157.png?v=gjdgxu"),
    ]

    name_to_id = {c.get("name"): c.get("id") for c in chars if isinstance(c, dict)}
    for name, expected_id, url in image_updates:
        cid = name_to_id.get(name)
        if cid != expected_id:
            raise RuntimeError(f"ID mismatch for {name}: expected {expected_id} got {cid}")
        ensure_thumb(int(cid), url)

    # 2) merges (keep smaller id, name=left side)
    pairs = [
        ("ハック（魚人）", "ハック"),
        ("鉄筋のスムージ", "スムージ"),
        ("ドンキホーテ・ミョスガルド聖", "ミョスガルド"),
        ("ロズワード・シャルリア宮", "シャルリア"),
        ("クラウ・D・クローバー", "クローバー"),
        ("クロ（クラハドール）", "キャプテン・クロ"),
    ]

    merged_results = []
    for left, right in pairs:
        keep_id, drop_id = merge_pair(chars, left, right)
        merged_results.append((left, right, keep_id, drop_id))

    chars.sort(key=lambda c: int(c.get("id", 0)) if isinstance(c, dict) else 0)
    CHAR_PATH.write_text(json.dumps(chars, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    print("image_updates_done", len(image_updates))
    for name, cid, _ in image_updates:
        print(f"IMAGE {name} id={cid}")

    print("merges_done", len(merged_results))
    for left, right, keep_id, drop_id in merged_results:
        print(f"MERGE {left}/{right} keep={keep_id} drop={drop_id}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

