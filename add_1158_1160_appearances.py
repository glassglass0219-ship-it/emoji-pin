#!/usr/bin/env python3
"""1158〜1160話の登場を characters.json に反映（通常は appearances、扉絵は covers）。"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAR_PATH = ROOT / "src/data/characters.json"

data_to_process = {
    1158: {
        "title": "ロックスvs.ハラルド",
        "normal": [
            "ゴール・D・ロジャー",
            "シルバーズ・レイリー",
            "スコッパー・ギャバン",
            "ムーン・アイザック・ジュニア",
            "ドンキーノ",
            "エリオ",
            "スペンサー",
            "ピータームー",
            "マックス・マルクス",
            "シーガルガンズ・ノズドン",
            "サンベル",
            "タロウ",
            "ガンリュウ",
            "C.B.ギャラント",
            "モモラ",
            "バンクロ",
            "ヤモン",
            "ロックス・D・ジーベック",
            "エドワード・ニューゲート",
            "ミス・バッキン",
            "オオク",
            "シャーロット・リンリン",
            "グロリオサ",
            "マーカス・マーズ",
            "トップマン・ワルキュリー",
            "エサンバロン・V・ヌスジュロ",
            "ユ・ペテロ",
            "フィガーランド・ガーリング",
            "ハラルド",
            "アイダ",
            "ハイルディン",
            "ロキ",
            "マト",
            "シャクヤク",
            "マグノリア",
            "フィガーランド・シャムロック",
            "シャンクス",
        ],
        "cover": ["ヤマト", "菊之丞", "チョウ"],
    },
    1159: {
        "title": "運命の島",
        "normal": [
            "ロックス・D・ジーベック",
            "エドワード・ニューゲート",
            "ミス・バッキン",
            "シキ",
            "オオク",
            "アマズイ",
            "マーロン",
            "キャプテン・ジョン",
            "シャーロット・リンリン",
            "ナポレオン",
            "シュトロイゼン",
            "カイドウ",
            "ギン",
            "グロリオサ",
            "ギル・バスター",
            "ゴール・D・ロジャー",
            "シルバーズ・レイリー",
            "スコッパー・ギャバン",
            "ドンキーノ",
            "シーガルガンズ・ノズドン",
            "モモラ",
            "フィガーランド・ガーリング",
            "シェパード・サマーズ",
            "マンマイヤー・グンコ",
            "モンキー・D・ガープ",
            "モンキー・D・ドラゴン",
            "バルトロメオ・クマ",
            "エンポリオ・イワンコフ",
            "ジニー",
            "ハラルド",
            "シャクヤク",
            "エリス",
            "マーシャル・D・ティーチ",
            "マグノリア",
            "フィガーランド・シャムロック",
            "シャンクス",
            "モーガンズ",
        ],
        "cover": ["ヤマト", "鬼丸", "うるティ", "ページワン"],
    },
    1160: {
        "title": "ゴッドバレー事件",
        "normal": [
            "ロックス・D・ジーベック",
            "エドワード_ニューゲート",
            "シキ",
            "ミス・バッキン",
            "キャプテン・ジョン",
            "シャーロット・リンリン",
            "ナポレオン",
            "シュトロイゼン",
            "バーベル",
            "カイドウ",
            "ギン",
            "グロリオサ",
            "ゴール_D_ロジャー",
            "シルバーズ・レイリー",
            "スコッパー・ギャバン",
            "ドンキーノ",
            "ピータームー",
            "ジャクソン・バナー",
            "マックス・マルクス",
            "タロウ",
            "モモラ",
            "ラングラム",
            "ムグレン",
            "ジェイガルシア・サターン",
            "フィガーランド・ガーリング",
            "シェパード・サマーズ",
            "サッチェルズ・マフィー",
            "マンマイヤー・グンコ",
            "モンキー・D・ガープ",
            "ボガード",
            "モンキー・D・ドラゴン",
            "バルトロメオ・クマ",
            "エンポリオ・イワンコフ",
            "シャクヤク",
            "エリス",
            "マーシャル・D・ティーチ",
            "マグノリア",
            "フィガーランド・シャムロック",
            "シャンクス",
        ],
        "cover": ["ヤマト"],
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
    "菊之丞": "菊",
    "バルトロメオ・クマ": "バーソロミュー・くま",
    "ユ・ペテロ": "シェパード・十・ピーター",
    "鬼丸": "牛鬼丸",
    "ゴール_D_ロジャー": "ゴール・D・ロジャー",
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

    if list_name == "ギン":
        for c in matches:
            nm = str(c.get("name") or "")
            if "ギン（ロジャー海賊団）" in nm or "ロジャー海賊団" in nm:
                return c
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
        "1158話〜1160話のアップデートが完了しました。"
        f" appearances 追加: {updated_app} / covers 追加: {updated_cov} / 新規: {new_n}"
    )


if __name__ == "__main__":
    run_update()
