#!/usr/bin/env python3
"""id 923 のキャラ「京」を「凶」に改名し、appearances を指定で上書き（covers は維持）。"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAR_PATH = ROOT / "src/data/characters.json"

NEW_APPEARANCES = [
    {"episode": 1156, "title": "アイドル"},
    {"episode": 1157, "title": "伝説のBAR"},
    {"episode": 1159, "title": "運命の島"},
    {"episode": 1160, "title": "ゴッドバレー事件"},
    {"episode": 1161, "title": "矢の雨をしのいで結ぶ恋の詩"},
    {"episode": 1162, "title": "Ｇ・Ｖ・Ｂ・Ｒ（ゴッドバレーバトルロワイヤル）"},
    {"episode": 1165, "title": "残響"},
]


def fix_kyo_character() -> None:
    with CHAR_PATH.open(encoding="utf-8") as f:
        chars: list[dict] = json.load(f)

    target: dict | None = None
    for c in chars:
        if isinstance(c, dict) and int(c.get("id", -1)) == 923:
            target = c
            break

    if target is None:
        print("⚠ id=923 のキャラクターが見つかりませんでした。")
        return

    if target.get("name") not in ("京", "凶"):
        print(f"⚠ id=923 の名前が想定外です: {target.get('name')!r}")
        return

    prev_cov = target.get("covers")
    target["name"] = "凶"
    target["appearances"] = [dict(x) for x in NEW_APPEARANCES]
    if isinstance(prev_cov, list) and len(prev_cov) > 0:
        target["covers"] = prev_cov
    elif "covers" not in target:
        target["covers"] = []
    target["firstAppearance"] = min(int(x["episode"]) for x in NEW_APPEARANCES)

    def patch_coapp_names(obj: object) -> None:
        if isinstance(obj, dict):
            if obj.get("id") == 923 and obj.get("name") == "京":
                obj["name"] = "凶"
            for v in obj.values():
                patch_coapp_names(v)
        elif isinstance(obj, list):
            for item in obj:
                patch_coapp_names(item)

    patch_coapp_names(chars)

    chars.sort(key=lambda x: int(x.get("id", 0)))

    with CHAR_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("✅ '京' を '凶' に修正し、appearances を上書きしました（1169 の covers は維持）。")


if __name__ == "__main__":
    fix_kyo_character()
