#!/usr/bin/env python3
"""ロイド→ロイダー、フィッシュボーン→Dr.フィッシュボーネン、ユイ→ユーイ と登場履歴のマージ。"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAR_PATH = ROOT / "src/data/characters.json"

UPDATES: list[dict] = [
    {
        "old_names": ("ロイド", "ロイダー"),
        "new_name": "ロイダー",
        "new_apps": [
            {"episode": 550, "title": "マリンフォード"},
            {"episode": 551, "title": "あの日"},
        ],
    },
    {
        "old_names": ("フィッシュボーン", "Dr.フィッシュボーネン"),
        "new_name": "Dr.フィッシュボーネン",
        "new_apps": [
            {"episode": 594, "title": "メッセージ"},
        ],
    },
    {
        "old_names": ("ユイ", "ユーイ"),
        "new_name": "ユーイ",
        "new_apps": [
            {"episode": 965, "title": "黒炭家の陰謀"},
            {"episode": 966, "title": "ロジャーと白ひげ"},
            {"episode": 968, "title": "おでんの帰還"},
            {"episode": 1096, "title": "くまの過去"},
            {"episode": 1160, "title": "ゴッドバレー事件"},
            {"episode": 1162, "title": "Ｇ・Ｖ・Ｂ・Ｒ"},
        ],
    },
]


def merge_appearances(
    existing: list[dict] | None, additions: list[dict]
) -> list[dict]:
    """話数で重複排除。同一話は既存タイトルを優先（1115話以降などを消さない）。"""
    by_ep: dict[int, str] = {}
    for a in existing or []:
        if not isinstance(a, dict) or "episode" not in a:
            continue
        ep = int(a["episode"])
        by_ep[ep] = str(a.get("title", ""))
    for a in additions:
        ep = int(a["episode"])
        if ep not in by_ep:
            by_ep[ep] = str(a.get("title", ""))
    return [{"episode": ep, "title": by_ep[ep]} for ep in sorted(by_ep)]


def patch_names_recursive(obj: object, old_names: tuple[str, ...], new_name: str) -> None:
    if isinstance(obj, dict):
        if obj.get("name") in old_names:
            obj["name"] = new_name
        for v in obj.values():
            patch_names_recursive(v, old_names, new_name)
    elif isinstance(obj, list):
        for item in obj:
            patch_names_recursive(item, old_names, new_name)


def run_fix() -> None:
    with CHAR_PATH.open(encoding="utf-8") as f:
        chars: list[dict] = json.load(f)

    for up in UPDATES:
        old_names = up["old_names"]
        new_name = up["new_name"]
        new_apps = up["new_apps"]
        hit = False
        for c in chars:
            if not isinstance(c, dict) or c.get("name") not in old_names:
                continue
            c["name"] = new_name
            c["appearances"] = merge_appearances(c.get("appearances"), new_apps)
            eps = [int(x["episode"]) for x in c["appearances"]]
            if eps:
                c["firstAppearance"] = min(eps)
            hit = True
            print(f"✅ '{new_name}' の名前と履歴を更新しました。")
            break
        if not hit:
            print(f"⚠ {old_names} に一致するトップレベルキャラが見つかりませんでした（{new_name}）。")

        patch_names_recursive(chars, old_names, new_name)

    chars.sort(key=lambda x: int(x.get("id", 0)))

    with CHAR_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)
        f.write("\n")


if __name__ == "__main__":
    run_fix()
