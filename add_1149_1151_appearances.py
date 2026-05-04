#!/usr/bin/env python3
"""1149〜1151話の登場を characters.json に反映（通常は appearances、扉絵は covers）。"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAR_PATH = ROOT / "src/data/characters.json"

data_to_process = {
    1149: {
        "title": "一秒",
        "normal": [
            "ナミ",
            "ウソップ",
            "トニートニー・チョッパー",
            "ニコ・ロビン",
            "ブルック",
            "ジンベエ",
            "ブロギー",
            "ジャルール",
            "ジャガー・D・サウロ",
            "アンジェ",
            "ブレード",
            "リプリー",
            "スコッパー・ギャバン",
            "イルヴァ",
            "スカルディ",
            "オラフ",
            "マグ",
            "ロンヤ",
            "カリン",
            "マガッタ",
            "ヨハンナ",
            "ビョルン",
            "ダイナ",
            "ネロナ・イム",
            "マンマイヤー・グンコ",
            "シェパード・サマーズ",
            "リモシフ・キリンガム",
        ],
        "cover": [
            "モンキー・D・ルフィ",
            "ロロノア・ゾロ",
            "サンジ",
            "ジュエリー・ボニー",
            "リリス",
        ],
    },
    1150: {
        "title": "黒転支配（ドミ・リバーシ）",
        "normal": [
            "ナミ",
            "ウソップ",
            "ニコ・ロビン",
            "ブルック",
            "ジンベエ",
            "ドリー",
            "ブロギー",
            "カーシー",
            "トルマン",
            "ジャルール",
            "ダイナ",
            "イルヴァ",
            "スカルディ",
            "オラフ",
            "カリン",
            "マグ",
            "ネロナ・イム",
            "マンマイヤー_グンコ",
            "シェパード・サマーズ",
            "リモシフ・キリンガム",
        ],
        "cover": ["ヤマト", "うるティ", "ページワン"],
    },
    1151: {
        "title": "もういいわかった!!!",
        "normal": [
            "モンキー・D・ルフィ",
            "ロロノア・ゾロ",
            "ナミ",
            "ウソップ",
            "サンジ",
            "トニートニー・チョッパー",
            "ニコ・ロビン",
            "ブルック",
            "ジンベエ",
            "ドリー",
            "ブロギー",
            "カーシー",
            "トルマン",
            "ハイルディン",
            "スタンセン",
            "ドウロ",
            "ゴールドバーグ",
            "ゲルズ",
            "リプリー",
            "スコッパー_ギャバン",
            "イルヴァ",
            "カリン",
            "マグ",
            "マガッタ",
            "ヨハンナ",
            "ビョルン",
            "ダイナ",
            "ロキ",
            "モザ",
            "ネロナ・イム",
            "マンマイヤー・グンコ",
            "シェパード・サマーズ",
            "リモシフ・キリンガム",
        ],
        "cover": ["ヤマト", "河松", "すねこすり"],
    },
}

SYNONYMS: dict[str, str] = {
    "ジャガー・D・サウロ": "ハグワール・D・サウロ",
    "スコッパー・ギャバン": "ギャバン",
    "スコッパー_ギャバン": "ギャバン",
    "マンマイヤー_グンコ": "マンマイヤー・グンコ",
    "ネロナ・イム": "イム",
}

NAME_EQUIV_CLASSES: tuple[frozenset[str], ...] = (
    frozenset({"雷ぞう", "ライゾウ"}),
)


def norm_key(s: str) -> str:
    t = re.sub(r"[・\s\-_]", "", (s or "").strip())
    while len(t) > 1 and t.endswith("聖"):
        t = t[:-1]
    return t


def equiv_norm_keys(nk: str) -> frozenset[str]:
    for grp in NAME_EQUIV_CLASSES:
        norms = frozenset(norm_key(x) for x in grp)
        if nk in norms:
            return norms
    return frozenset({nk})


def variant_keys(list_name: str) -> set[str]:
    resolved = SYNONYMS.get(list_name, list_name.replace("_", "・"))
    keys: set[str] = set()
    for base in {list_name, resolved, list_name.replace("_", "・")}:
        if not base:
            continue
        keys.update(equiv_norm_keys(norm_key(base)))
        if base.startswith("光月") and len(base) > 2:
            keys.update(equiv_norm_keys(norm_key(base[2:])))
    return keys


def character_norm_keys(c: dict) -> set[str]:
    keys: set[str] = set()
    nm = c.get("name") or ""
    keys.update(equiv_norm_keys(norm_key(nm)))
    if nm.startswith("光月") and len(nm) > 2:
        keys.update(equiv_norm_keys(norm_key(nm[2:])))
    al = str(c.get("alias") or "")
    for part in re.split(r"[,、／/]", al):
        p = part.strip()
        if p:
            keys.update(equiv_norm_keys(norm_key(p)))
    return keys


def find_character(chars: list[dict], list_name: str) -> dict | None:
    wanted = variant_keys(list_name)
    for c in chars:
        if not isinstance(c, dict) or "name" not in c:
            continue
        if character_norm_keys(c) & wanted:
            return c
    return None


def storage_name(list_name: str) -> str:
    if list_name in SYNONYMS:
        return SYNONYMS[list_name]
    return list_name.replace("_", "・")


def _ep_sort_key(x: dict) -> int:
    try:
        return int(x.get("episode"))
    except (TypeError, ValueError):
        return 0


def append_entry(target: dict, key: str, ep_num: int, title: str) -> bool:
    arr = target.setdefault(key, [])
    if not isinstance(arr, list):
        return False
    if any(isinstance(a, dict) and int(a.get("episode", -1)) == ep_num for a in arr):
        return False
    arr.append({"episode": ep_num, "title": title})
    arr.sort(key=_ep_sort_key)
    return True


def new_character_stub(char_id: int, list_name: str, key: str, ep: int, title: str) -> dict:
    name = storage_name(list_name)
    base: dict = {
        "id": char_id,
        "name": name,
        "reading": "",
        "gender": "",
        "affiliation": "",
        "devilFruit": "",
        "bounty": "",
        "birthday": "",
        "firstAppearance": ep,
    }
    if key == "appearances":
        base["appearances"] = [{"episode": ep, "title": title}]
    else:
        base["appearances"] = []
        base["covers"] = [{"episode": ep, "title": title}]
    return base


def run_update() -> None:
    with CHAR_PATH.open(encoding="utf-8") as f:
        chars: list[dict] = json.load(f)

    ids = [int(c["id"]) for c in chars if isinstance(c, dict) and "id" in c]
    next_id = max(ids) + 1 if ids else 1
    updated_app = 0
    updated_cov = 0
    new_n = 0

    for ep_num in sorted(data_to_process.keys()):
        info = data_to_process[ep_num]
        title = info["title"]
        cover_title = f"{title}の扉絵"

        for list_name in info["normal"]:
            target = find_character(chars, list_name)
            if target is not None:
                if append_entry(target, "appearances", ep_num, title):
                    updated_app += 1
            else:
                chars.append(
                    new_character_stub(next_id, list_name, "appearances", ep_num, title)
                )
                print(f"✨ 新規登録(本編): {storage_name(list_name)} (id={next_id}, ep={ep_num})")
                next_id += 1
                new_n += 1

        for list_name in info["cover"]:
            target = find_character(chars, list_name)
            if target is not None:
                if append_entry(target, "covers", ep_num, cover_title):
                    updated_cov += 1
            else:
                chars.append(
                    new_character_stub(next_id, list_name, "covers", ep_num, cover_title)
                )
                print(f"✨ 新規登録(扉絵): {storage_name(list_name)} (id={next_id}, ep={ep_num})")
                next_id += 1
                new_n += 1

    chars.sort(key=lambda x: int(x["id"]))

    with CHAR_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(
        "1149話〜1151話のアップデートが完了しました。"
        f" appearances 追加: {updated_app} / covers 追加: {updated_cov} / 新規: {new_n}"
    )


if __name__ == "__main__":
    run_update()
