#!/usr/bin/env python3
"""ロジャー海賊団関連キャラの正式名へ一括改名（appearances / id は維持）。"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAR_PATH = ROOT / "src/data/characters.json"


def normalize(name: str) -> str:
    return re.sub(r"[・\s\-]", "", (name or "").strip())


RENAME_BY_NORM: dict[str, str] = {
    normalize("モモラ"): "Mr.モモラ",
    normalize("C.B.ギャラント"): "CBギャラン",
    normalize("シーガルガンズ・ノズドン"): "シーガル・ガンズ・ノズドン",
    normalize("ムーン・アイザック・ジュニア"): "ムーン・アイザックJr.",
    normalize("マックス・マルクス"): "マックスマークス",
    normalize("ムグレン"): "ミュグレン大佐",
    normalize("ガンリュウ"): "眼竜",
}


def patch_names(obj: object, rename_by_norm: dict[str, str], changes: list[tuple[str, str]]) -> None:
    if isinstance(obj, dict):
        if "name" in obj and isinstance(obj["name"], str):
            nk = normalize(obj["name"])
            if nk in rename_by_norm:
                new_name = rename_by_norm[nk]
                old_name = obj["name"]
                if old_name != new_name:
                    changes.append((old_name, new_name))
                    obj["name"] = new_name
        for v in obj.values():
            patch_names(v, rename_by_norm, changes)
    elif isinstance(obj, list):
        for item in obj:
            patch_names(item, rename_by_norm, changes)


def run_fix() -> None:
    with CHAR_PATH.open(encoding="utf-8") as f:
        chars: list[dict] = json.load(f)

    top_level_before = sum(
        1
        for c in chars
        if isinstance(c, dict) and normalize(c.get("name", "")) in RENAME_BY_NORM
    )

    changes: list[tuple[str, str]] = []
    patch_names(chars, RENAME_BY_NORM, changes)

    chars.sort(key=lambda x: int(x.get("id", 0)))

    with CHAR_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)
        f.write("\n")

    for old, new in sorted(set(changes), key=lambda x: x[0]):
        print(f"✅ '{old}' -> '{new}' に更新")

    print(f"\n完了！ トップレベルキャラで {top_level_before} 名の名前を修正しました（JSON 全体の name も同期）。")


if __name__ == "__main__":
    run_fix()
