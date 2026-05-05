#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def first_arc(c: dict[str, Any]) -> str:
    arcs = c.get("arcs")
    if isinstance(arcs, list) and arcs:
        v = arcs[0]
        if isinstance(v, str):
            return v
    return ""


def group_name(c: dict[str, Any]) -> str:
    g = c.get("group")
    if isinstance(g, str):
        return g
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(description="characters.json と thumbnails を突合して不足画像をCSV出力")
    ap.add_argument("--characters", default="src/data/characters.json")
    ap.add_argument("--thumb-dir", default="public/images/thumbnails")
    ap.add_argument("--output", default="missing_images_list.csv")
    args = ap.parse_args()

    char_path = Path(args.characters)
    thumb_dir = Path(args.thumb_dir)
    out_path = Path(args.output)

    chars = json.loads(char_path.read_text(encoding="utf-8"))
    if not isinstance(chars, list):
        raise SystemExit("characters.json は配列である必要があります")

    missing: list[tuple[int, str, str, str]] = []
    for row in chars:
        if not isinstance(row, dict):
            continue
        try:
            cid = int(row.get("id"))
        except Exception:
            continue
        name = str(row.get("name") or "").strip()
        thumb_path = thumb_dir / f"{cid}.webp"
        if not thumb_path.exists():
            missing.append((cid, name, first_arc(row), group_name(row)))

    missing.sort(key=lambda x: x[0])

    with out_path.open("w", encoding="utf-8-sig", newline=""):
        pass
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ID", "名前", "登場編", "組織名"])
        for cid, name, arc, group in missing:
            w.writerow([cid, name, arc, group])

    print(f"Wrote {out_path} ({len(missing)} missing)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

