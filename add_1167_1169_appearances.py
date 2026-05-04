#!/usr/bin/env python3
"""1167〜1169話の登場を characters.json に反映（通常は appearances、扉絵は covers）。"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAR_PATH = ROOT / "src/data/characters.json"

data_to_process = {
    1167: {
        "title": "イーダの息子",
        "normal": [
            "ゴール・D・ロジャー",
            "シルバーズ・レイリー",
            "スコッパー・ギャバン",
            "クロッカス",
            "エリオ",
            "スペンサー",
            "マックス・マルクス",
            "ムグレン",
            "バギー",
            "カイドウ",
            "シャーロット・リンリン",
            "ナポレオン",
            "エドワード・ニューゲート",
            "シキ",
            "フィッシャー・タイガー",
            "ジェイガルシア・サターン",
            "マーカス・マーズ",
            "トップマン・ワルキュリー",
            "エサンバロン・V・ヌスジュロ",
            "シェパード・十・ピーター",
            "フィガーランド・ガーリング",
            "シェパード・サマーズ",
            "フィガーランド・シャムロック",
            "シャンクス",
            "ラクロワ",
            "ボア・ハンコック",
            "ボア・サンダーソニア",
            "ボア・マリーゴールド",
            "コアラ",
            "ハラルド",
            "アイダ",
            "ジャガー・D・サウロ",
            "リプリー",
            "ハイルディン",
            "スタンセン",
            "ドウロ",
            "ゴールドバーグ",
            "ゲルズ",
            "マト",
            "ロキ",
            "ナッシュ",
            "オオク",
            "ネプチューン",
            "乙姫",
            "フカボシ",
            "リュウボシ",
            "マンボシ",
            "モーガンズ",
            "ロイダー",
            "まだら",
        ],
        "cover": ["ゲンぞう", "ノジコ"],
    },
    1168: {
        "title": "エルバフの雪",
        "normal": [
            "ネロナ・イム",
            "ジェイガルシア・サターン",
            "マーカス・マーズ",
            "トップマン・ワルキュリー",
            "エサンバロン・V・ヌスジュロ",
            "シェパード・十・ピーター",
            "ハラルド",
            "ロキ",
            "アイダ",
            "ジャルール",
            "ジャガー・D・サウロ",
            "リプリー",
            "スコッパー・ギャバン",
            "大腸",
            "ハイルディン",
            "スタンセン",
            "ドウロ",
            "ゴールドバーグ",
            "ゲルズ",
            "マト",
            "ウミット",
        ],
        "cover": ["はっちゃん"],
    },
    1169: {
        "title": "一刻も早く死ななくては",
        "normal": [
            "ハラルド",
            "ロキ",
            "ジャルール",
            "スコッパー・ギャバン",
            "リプリー",
            "大腸",
            "ジャガー・D・サウロ",
            "ネロナ・イム",
            "シャンクス",
        ],
        "cover": [
            "ロックス・D・ジーベック",
            "エドワード・ニューゲート",
            "シキ",
            "ミス・バッキン",
            "マーロン",
            "オオク",
            "アマズイ",
            "キャプテン・ジョン",
            "シャーロット・リンリン",
            "ナポレオン",
            "シュトロイゼン",
            "バーベル",
            "カイドウ",
            "京",
            "グロリオサ",
        ],
    },
}

# 提供リストの揺れ → JSON 上の canonical（storage_name）
SYNONYMS: dict[str, str] = {
    "ジャガー・D・サウロ": "ハグワール・D・サウロ",
    "ジャガー・D・ソール": "ハグワール・D・サウロ",
    "スコッパー・ギャバン": "ギャバン",
    "スコーパー・ガバン": "ギャバン",
    "スコーパー・ギャバン": "ギャバン",
    "ネロナ・イム": "イム",
    "シキ": "金獅子",
    "式": "金獅子",
    "シャーロット・リンリン": "ビッグ・マム",
    "ジェイガルシア・サターン": "ジェイガルシア・サターン聖",
    "トップマン・ワルキュリー": "トップマン・ウォーキュリー",
    "エサンバロン・V・ヌスジュロ": "イーザンバロン・V・ナス寿郎",
    "グロリオサ": "グロリオーサ",
    "ゼウス": "ゼウス・ブリーズテンポ",
    "菊之丞": "菊",
    "バルトロメオ・クマ": "バーソロミュー・くま",
    "バーソロミュー・クマ": "バーソロミュー・くま",
    "ユ・ペテロ": "シェパード・十・ピーター",
    "羊飼いユ・ペテロ": "シェパード・十・ピーター",
    "鬼丸": "牛鬼丸",
    "ゴール_D_ロジャー": "ゴール・D・ロジャー",
    "トラファルガー・D・ワーテル・ロー": "トラファルガー・ロー",
    "ジャルル": "ジャルール",
    "マーシャル_D_ティーチ": "マーシャル・D・ティーチ",
    "エンポリオ_イワンコフ": "エンポリオ・イワンコフ",
    "海藤": "カイドウ",
    "ハジルディン": "ハイルディン",
    "道路": "ドウロ",
    "ロード": "ドウロ",
    "ゲルド": "ゲルズ",
    "海王星": "ネプチューン",
    "深星": "フカボシ",
    "龍星": "リュウボシ",
    "満星": "マンボシ",
    "ハッチャン": "はっちゃん",
    "ロックス・D・ゼベック": "ロックス・D・ジーベック",
    "乙姫": "オトヒメ",
    "ゲンぞう": "ゲンゾウ",
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
                print(f"✨ 新規(本編): {stub['name']} (id={next_id}, ep={ep_num})")
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
                print(f"✨ 新規(扉絵): {stub['name']} (id={next_id}, ep={ep_num})")
                next_id += 1
                new_n += 1

    chars.sort(key=lambda x: int(x["id"]))

    with CHAR_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(
        "1167話〜1169話のアップデート完了。"
        f" appearances 追加: {updated_app} / covers 追加: {updated_cov} / 新規: {new_n}"
    )


if __name__ == "__main__":
    run_update()
