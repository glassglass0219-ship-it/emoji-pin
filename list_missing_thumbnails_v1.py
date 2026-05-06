#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
from pathlib import Path


CHAR_PATH = Path("src/data/characters.json")
THUMBS_DIR = Path("public/images/thumbnails")
OUT_CSV = Path("missing_images_list.csv")


def norm_list(v: object) -> list[str]:
    if isinstance(v, list):
        return [str(x) for x in v if str(x).strip()]
    if isinstance(v, str) and v.strip():
        return [v.strip()]
    return []


def main() -> int:
    chars = json.loads(CHAR_PATH.read_text(encoding="utf-8"))
    if not isinstance(chars, list):
        raise SystemExit("characters.json must be a list")

    missing_rows = []
    for c in chars:
        if not isinstance(c, dict):
            continue
        cid = c.get("id")
        name = c.get("name")
        if not isinstance(cid, int) or not isinstance(name, str):
            continue
        if not (THUMBS_DIR / f"{cid}.webp").exists():
            arcs = norm_list(c.get("arcs"))
            groups = norm_list(c.get("group"))
            cats = norm_list(c.get("category"))
            # keep the existing CSV shape: ID,名前,登場編,組織名
            arc_str = "/".join(arcs)
            org_str = "/".join([*cats, *groups])
            missing_rows.append((cid, name, arc_str, org_str))

    missing_rows.sort(key=lambda r: r[0])

    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ID", "名前", "登場編", "組織名"])
        w.writerows(missing_rows)

    print(f"missing_thumbnail_count={len(missing_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

