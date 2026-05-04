#!/usr/bin/env python3
"""fix_names_v3 誤統合の修復: id39 をクリークのギンに戻し、凶(id923)を復元。"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAR_PATH = ROOT / "src/data/characters.json"

KYO_APPEARANCES = [
    {"episode": 1156, "title": "アイドル"},
    {"episode": 1157, "title": "伝説のBAR"},
    {"episode": 1159, "title": "運命の島"},
    {"episode": 1160, "title": "ゴッドバレー事件"},
    {"episode": 1161, "title": "矢の雨をしのいで結ぶ恋の詩"},
    {"episode": 1162, "title": "Ｇ・Ｖ・Ｂ・Ｒ（ゴッドバレーバトルロワイヤル）"},
    {"episode": 1165, "title": "残響"},
]
KYO_COVERS = [{"episode": 1169, "title": "一刻も早く死ななくてはの扉絵"}]


def run_recover() -> None:
    with CHAR_PATH.open(encoding="utf-8") as f:
        chars: list[dict] = json.load(f)

    c39: dict | None = None
    for c in chars:
        if isinstance(c, dict) and int(c.get("id", -1)) == 39:
            c39 = c
            break
    if c39 is None:
        print("⚠ id 39 が見つかりません")
        return

    apps = c39.get("appearances") or []
    early = [dict(a) for a in apps if isinstance(a, dict) and int(a.get("episode", 0)) < 1000]
    legend = [dict(a) for a in apps if isinstance(a, dict) and int(a.get("episode", 0)) >= 1000]

    c39["name"] = "ギン"
    c39["appearances"] = sorted(early, key=lambda x: int(x["episode"]))
    c39["covers"] = []
    eps = [int(x["episode"]) for x in c39["appearances"]]
    c39["firstAppearance"] = min(eps) if eps else 44

    if any(isinstance(c, dict) and int(c.get("id", -1)) == 923 for c in chars):
        print("⚠ id 923 が既に存在するためスキップ")
    else:
        by_ep: dict[int, dict] = {}
        for a in KYO_APPEARANCES:
            by_ep[int(a["episode"])] = dict(a)
        for a in legend:
            ep = int(a["episode"])
            if ep not in by_ep:
                by_ep[ep] = dict(a)
        kyo_apps = [by_ep[e] for e in sorted(by_ep)]

        chars.append(
            {
                "id": 923,
                "name": "凶",
                "reading": "",
                "gender": "",
                "affiliation": "",
                "devilFruit": "",
                "bounty": "",
                "birthday": "",
                "firstAppearance": min(by_ep) if by_ep else 1156,
                "appearances": kyo_apps,
                "covers": list(KYO_COVERS),
            }
        )
        print("✅ id 923 凶 を復元しました")

    print("✅ id 39 をギンに戻しました")

    chars.sort(key=lambda x: int(x.get("id", 0)))

    with CHAR_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)
        f.write("\n")


if __name__ == "__main__":
    run_recover()
