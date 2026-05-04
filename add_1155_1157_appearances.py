#!/usr/bin/env python3
"""1155〜1157話の登場を characters.json に反映（通常は appearances、扉絵は covers）。"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAR_PATH = ROOT / "src/data/characters.json"

data_to_process = {
    1155: {
        "title": "ロックス海賊団",
        "normal": [
            "ロックス・D・ジーベック",
            "エドワード・ニューゲート",
            "シキ",
            "ミス・バッキン",
            "マーロン",
            "オオク",
            "アマズイ",
            "ネロナ・イム",
            "マンマイヤー・グンコ",
            "ハラルド",
            "ロキ",
        ],
        "cover": [
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
        ],
    },
    1156: {
        "title": "アイドル",
        "normal": [
            "グロリオサ",
            "シャクヤク",
            "トリトマ",
            "ロックス・D・ジーベック",
            "エドワード・ニューゲート",
            "シキ",
            "ミス・バッキン",
            "マーロン",
            "オオク",
            "アマズイ",
            "シャーロット・リンリン",
            "カイドウ",
            "キャプテン・ジョン",
            "シュトロイゼン",
            "ギン",
            "バーベル",
            "ゴール・D・ロジャー",
            "シルバーズ・レイリー",
            "スコッパー・ギャバン",
            "ドンキーノ",
            "キビパイン",
            "スペンサー",
            "サンベル",
            "ガンリュウ",
            "ラングラム",
            "ムグレン",
            "マックス・マルクス",
            "モンキー_D_ガープ",
            "ハラルド",
            "アイダ",
            "ハイルディン",
            "ロキ",
            "マト",
        ],
        "cover": [
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
        ],
    },
    1157: {
        "title": "伝説のBAR",
        "normal": [
            "ロックス・D・ジーベック",
            "エドワード・ニューゲート",
            "シキ",
            "ミス・バッキン",
            "マーロン",
            "オオク",
            "アマズイ",
            "シャーロット・リンリン",
            "カイドウ",
            "キャプテン・ジョン",
            "シュトロイゼン",
            "ギン",
            "バーベル",
            "グロリオサ",
            "プロメテウス",
            "ゼウス",
            "ジェイガルシア・サターン",
            "マーカス・マーズ",
            "トップマン・ワルキュリー",
            "エサンバロン・V・ヌスジュロ",
            "コング",
            "モンキー・D・ガープ",
            "センゴク",
            "つる",
            "ジョン・ジャイアント",
            "ハラルド",
            "アイダ",
            "ハイルディン",
            "ロキ",
            "マト",
            "シャクヤク",
            "シャーロット・カタクリ",
            "シャーロット・ダイフク",
            "シャーロット・オーブン",
        ],
        "cover": ["ヤマト", "菊之丞", "チョウ", "うるティ", "ページワン"],
    },
}

SYNONYMS: dict[str, str] = {
    "ジャガー・D・サウロ": "ハグワール・D・サウロ",
    "スコッパー・ギャバン": "ギャバン",
    "ネロナ・イム": "イム",
    "シキ": "金獅子",
    "シャーロット・リンリン": "ビッグ・マム",
    "ジェイガルシア・サターン": "ジェイガルシア・サターン聖",
    "トップマン・ワルキュリー": "トップマン・ウォーキュリー",
    "エサンバロン・V・ヌスジュロ": "イーザンバロン・V・ナス寿郎",
    "グロリオサ": "グロリオーサ",
    "ゼウス": "ゼウス・ブリーズテンポ",
    "モンキー_D_ガープ": "モンキー・D・ガープ",
    "菊之丞": "菊",
}

NAME_EQUIV_CLASSES: tuple[frozenset[str], ...] = (
    frozenset({"つる", "鶴"}),
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
    matches: list[dict] = []
    for c in chars:
        if not isinstance(c, dict) or "name" not in c:
            continue
        if character_norm_keys(c) & wanted:
            matches.append(c)

    if not matches:
        return None

    # 「ギン」はクリーク海賊団の既存キャラと同表記で衝突 → ロジャー海賊団所属のみ採用
    if list_name == "ギン":
        for c in matches:
            aff = str(c.get("affiliation") or "")
            if "ロジャー" in aff:
                return c
        return None

    if len(matches) == 1:
        return matches[0]
    return matches[0]


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
    # ロジャー海賊団のギン（既存はクリーク海賊団のギン）
    if list_name == "ギン":
        name = "ギン（ロジャー海賊団）"
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
    if list_name == "ギン":
        base["alias"] = "ギン"
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
                stub = new_character_stub(next_id, list_name, "appearances", ep_num, title)
                chars.append(stub)
                print(f"✨ 新規登録(本編): {stub['name']} (id={next_id}, ep={ep_num})")
                next_id += 1
                new_n += 1

        for list_name in info["cover"]:
            target = find_character(chars, list_name)
            if target is not None:
                if append_entry(target, "covers", ep_num, cover_title):
                    updated_cov += 1
            else:
                stub = new_character_stub(next_id, list_name, "covers", ep_num, cover_title)
                chars.append(stub)
                print(f"✨ 新規登録(扉絵): {stub['name']} (id={next_id}, ep={ep_num})")
                next_id += 1
                new_n += 1

    chars.sort(key=lambda x: int(x["id"]))

    with CHAR_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(
        "1155話〜1157話のアップデートが完了しました。"
        f" appearances 追加: {updated_app} / covers 追加: {updated_cov} / 新規: {new_n}"
    )


if __name__ == "__main__":
    run_update()
