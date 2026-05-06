#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="指定IDを characters.json と thumbnails から削除")
    ap.add_argument("--characters", default="src/data/characters.json")
    ap.add_argument("--thumb-dir", default="public/images/thumbnails")
    args = ap.parse_args()

    char_path = Path(args.characters)
    thumb_dir = Path(args.thumb_dir)

    delete_ids = {
        168: "大蛇",
        227: "11人の陪審員",
        233: "シルバー電伝虫",
        371: "白電伝虫",
        425: "タマゴ",
        427: "竜",
        442: "スライム",
        446: "竜 (小型)",
        630: "シャーロット・コーエン",
        681: "鎌ぞう",
        798: "シグ",
        806: "うさぎヘビ",
        809: "アン・ゼンカイナ",
        859: "オラフ",
        872: "ヨルムンガンド",
        875: "ニーズヘッグ",
        876: "モサ公",
        914: "ボガード",
        921: "マダラ",
        924: "ラグニル",
        927: "D. D. ティー",
        928: "ローズ",
        929: "ガントニオ",
    }

    chars = json.loads(char_path.read_text(encoding="utf-8"))
    if not isinstance(chars, list):
        raise SystemExit("characters.json は配列である必要があります")

    before = len(chars)
    kept: list[dict] = []
    deleted_rows: list[dict] = []

    for c in chars:
        if not isinstance(c, dict):
            continue
        cid = c.get("id")
        try:
            cid_int = int(cid)
        except Exception:
            kept.append(c)
            continue
        if cid_int in delete_ids:
            deleted_rows.append({"id": cid_int, "name": str(c.get("name") or "")})
            continue
        kept.append(c)

    kept.sort(key=lambda x: int(str(x.get("id", 0)) or 0))
    char_path.write_text(json.dumps(kept, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    deleted_images = 0
    for cid in delete_ids.keys():
        p = thumb_dir / f"{cid}.webp"
        if p.exists():
            p.unlink()
            deleted_images += 1

    after = len(kept)
    deleted_count = before - after

    print(f"削除（データ）件数: {deleted_count}")
    print(f"削除（画像）枚数: {deleted_images}")
    if deleted_rows:
        print("削除したID:")
        for r in sorted(deleted_rows, key=lambda x: x["id"]):
            print(f"  - {r['id']} {r['name']}")
    missing = sorted([cid for cid in delete_ids.keys() if cid not in {r['id'] for r in deleted_rows}])
    if missing:
        print("characters.json に存在せず未削除のID:")
        for cid in missing:
            print(f"  - {cid} ({delete_ids[cid]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

