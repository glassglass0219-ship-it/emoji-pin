#!/usr/bin/env python3
"""「マトラ」「まだら」を「マダラ」に統一し、appearances を指定リストで上書き（covers は維持）。"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAR_PATH = ROOT / "src/data/characters.json"

NEW_APPEARANCES = [
    {"episode": 101, "title": "リヴァース・マウンテン"},
    {"episode": 647, "title": "自由の国へ"},
    {"episode": 648, "title": "正体"},
    {"episode": 1115, "title": "大陸の断片"},
    {"episode": 1167, "title": "イーダの息子"},
    {"episode": 1168, "title": "エルバフの雪"},
    {"episode": 1169, "title": "一刻も早く死ななくては"},
]


def rename_matora_names(obj: object) -> None:
    """name が「マトラ」「まだら」のオブジェクトを「マダラ」に。"""
    if isinstance(obj, dict):
        n = obj.get("name")
        if n == "マトラ" or n == "まだら":
            obj["name"] = "マダラ"
        for v in obj.values():
            rename_matora_names(v)
    elif isinstance(obj, list):
        for item in obj:
            rename_matora_names(item)


def dedupe_by_episode(apps: list[dict]) -> list[dict]:
    seen: set[int] = set()
    out: list[dict] = []
    for a in sorted(apps, key=lambda x: int(x["episode"])):
        ep = int(a["episode"])
        if ep in seen:
            continue
        seen.add(ep)
        out.append({"episode": ep, "title": a["title"]})
    return out


def fix_matora_to_madara() -> None:
    with CHAR_PATH.open(encoding="utf-8") as f:
        chars: list[dict] = json.load(f)

    target: dict | None = None
    for c in chars:
        if not isinstance(c, dict):
            continue
        if c.get("name") in ("マトラ", "まだら", "マダラ") and int(c.get("id", -1)) == 921:
            target = c
            break
    if target is None:
        for c in chars:
            if isinstance(c, dict) and c.get("name") in ("マトラ", "まだら"):
                target = c
                break

    if target is None:
        print("⚠ 対象のキャラクター（マトラ / まだら）が見つかりませんでした。")
        return

    prev_cov = target.get("covers")
    target["name"] = "マダラ"
    target["appearances"] = dedupe_by_episode([dict(x) for x in NEW_APPEARANCES])
    if isinstance(prev_cov, list) and len(prev_cov) > 0:
        target["covers"] = prev_cov
    elif "covers" not in target:
        target["covers"] = []

    target["firstAppearance"] = min(int(x["episode"]) for x in target["appearances"])

    rename_matora_names(chars)

    chars.sort(key=lambda x: int(x.get("id", 0)))

    with CHAR_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print("✅ 'マトラ' / 'まだら' を 'マダラ' に統一し、appearances を更新しました（covers は維持）。")


if __name__ == "__main__":
    fix_matora_to_madara()
