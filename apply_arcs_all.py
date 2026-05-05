#!/usr/bin/env python3
"""全キャラに arcs: [] を付与し、WT100 face 0001〜0122 にマッチしたキャラへ東の海編を追加。"""
from __future__ import annotations

import json
import os
import time

import sync_images as si

EAST_BLUE_ARC = "東の海（イーストブルー）編"


def append_arc_unique(char: dict, arc: str) -> bool:
    arcs = char.setdefault("arcs", [])
    if arc not in arcs:
        arcs.append(arc)
        return True
    return False


def main() -> None:
    os.chdir(si.ROOT)

    with si.CHAR_PATH.open(encoding="utf-8") as f:
        chars: list[dict] = json.load(f)

    for c in chars:
        if isinstance(c, dict):
            c.setdefault("arcs", [])

    ja = si.scrape_midterm_alt_map(si.JA_MIDTERM)
    time.sleep(0.35)
    en = si.scrape_midterm_alt_map(si.EN_MIDTERM)
    ov = si.load_face_overrides(si.OVERRIDES_PATH)
    renames = si.load_renames(si.CORRECTIONS_PATH)

    touched_ids: set[int] = set()
    for i in si.FACE_RANGE:
        fid = f"{i:04d}"
        row = si.build_row(fid, ja, en, ov)
        if not row:
            continue
        ch = si.find_character(chars, row.get("name_ja") or "", row.get("name_en") or "", renames)
        if not ch:
            continue
        cid = int(ch["id"])
        if cid in touched_ids:
            continue
        if append_arc_unique(ch, EAST_BLUE_ARC):
            touched_ids.add(cid)

    chars.sort(key=lambda x: int(x.get("id", 0)))

    with si.CHAR_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"✅ arcs フィールドを全キャラに付与しました。")
    print(f"✅ 「{EAST_BLUE_ARC}」を {len(touched_ids)} 名に追加しました（WT100 0001〜0122 で名前が解決しマッチしたキャラ）。")


if __name__ == "__main__":
    main()
