#!/usr/bin/env python3
"""1128〜1130話の登場キャラを characters.json に反映する。"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAR_PATH = ROOT / "src/data/characters.json"

data_to_add = {
    1128: {
        "title": "RPG",
        "chars": [
            "モンキー・D・ルフィ",
            "ロロノア・ゾロ",
            "ナミ",
            "ウソップ",
            "サンジ",
            "トニートニー・チョッパー",
            "ニコ・ロビン",
            "フランキー",
            "ブルック",
            "ジンベエ",
            "太陽神",
            "ヒルムンガルド",
            "ムギン",
            "イスカット",
        ],
    },
    1129: {
        "title": "生人形（リドール）",
        "chars": [
            "モンキー・D・ルフィ",
            "ロロノア・ゾロ",
            "ナミ",
            "ウソップ",
            "サンジ",
            "トニートニー・チョッパー",
            "ゼウス",
            "ハイルディン",
            "ドウロ",
            "イスカット",
            "ヒルムンガルド",
            "ムギン",
            "グラットバニー",
            "ヤマト",
            "しのぶ",
            "お玉",
            "小紫",
        ],
    },
    1130: {
        "title": "呪いの王子",
        "chars": [
            "モンキー・D・ルフィ",
            "ロロノア・ゾロ",
            "ナミ",
            "ウソップ",
            "サンジ",
            "トニートニー・チョッパー",
            "ニコ・ロビン",
            "フランキー",
            "ブルック",
            "ジンベエ",
            "ドリー",
            "ブロギー",
            "オイモ",
            "カーシー",
            "ゴールドバーグ",
            "ゲルズ",
            "パイパー",
            "ナッシュ",
            "イスカット",
            "ベガパンク",
            "リリス",
            "ロキ",
            "ヤマト",
            "お玉",
        ],
    },
}

SYNONYMS: dict[str, str] = {
    "ゼウス": "ゼウス・ブリーズテンポ",
    "太陽神": "モンキー・D・ルフィ",
}


def norm_key(s: str) -> str:
    t = re.sub(r"[・\s\-_]", "", (s or "").strip())
    while len(t) > 1 and t.endswith("聖"):
        t = t[:-1]
    return t


def variant_keys(list_name: str) -> set[str]:
    resolved = SYNONYMS.get(list_name, list_name.replace("_", "・"))
    keys: set[str] = set()
    for base in {list_name, resolved, list_name.replace("_", "・")}:
        if not base:
            continue
        keys.add(norm_key(base))
        if base.startswith("光月") and len(base) > 2:
            keys.add(norm_key(base[2:]))
    return keys


def find_character(chars: list[dict], list_name: str) -> dict | None:
    keys = variant_keys(list_name)
    for c in chars:
        if not isinstance(c, dict) or "name" not in c:
            continue
        nm = c.get("name") or ""
        if norm_key(nm) in keys:
            return c
        al = str(c.get("alias") or "")
        for part in re.split(r"[,、／/]", al):
            p = part.strip()
            if p and norm_key(p) in keys:
                return c
    return None


def storage_name(list_name: str) -> str:
    if list_name in SYNONYMS:
        return SYNONYMS[list_name]
    return list_name.replace("_", "・")


def new_character_stub(char_id: int, list_name: str, ep: int, title: str) -> dict:
    name = storage_name(list_name)
    return {
        "id": char_id,
        "name": name,
        "reading": "",
        "gender": "",
        "affiliation": "",
        "devilFruit": "",
        "bounty": "",
        "birthday": "",
        "firstAppearance": ep,
        "appearances": [{"episode": ep, "title": title}],
    }


def run_update() -> None:
    with CHAR_PATH.open(encoding="utf-8") as f:
        chars: list[dict] = json.load(f)

    next_id = max(int(c["id"]) for c in chars if isinstance(c, dict) and "id" in c) + 1
    updated = 0
    new_n = 0

    for ep_num in sorted(data_to_add.keys()):
        info = data_to_add[ep_num]
        title = info["title"]
        for list_name in info["chars"]:
            target = find_character(chars, list_name)
            if target is not None:
                apps = target.setdefault("appearances", [])
                if not isinstance(apps, list):
                    continue
                has_ep = any(
                    isinstance(a, dict) and int(a.get("episode", -1)) == ep_num for a in apps
                )
                if not has_ep:
                    apps.append({"episode": ep_num, "title": title})

                    def _ep_key(x: dict) -> int:
                        try:
                            return int(x.get("episode"))
                        except (TypeError, ValueError):
                            return 0

                    apps.sort(key=_ep_key)
                    updated += 1
            else:
                chars.append(new_character_stub(next_id, list_name, ep_num, title))
                print(f"[NEW] {storage_name(list_name)} (id={next_id}, ep={ep_num})")
                next_id += 1
                new_n += 1

    chars.sort(key=lambda x: int(x["id"]))

    with CHAR_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"完了。既存へ登場追加: {updated} 件 / 新規: {new_n} 件")


if __name__ == "__main__":
    run_update()
