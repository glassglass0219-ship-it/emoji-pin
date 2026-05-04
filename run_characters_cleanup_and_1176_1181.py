#!/usr/bin/env python3
"""characters.json: 誤字名の統一（リネーム）と 1176〜1181 話の appearances / covers 追加。"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAR_PATH = ROOT / "src/data/characters.json"

# 旧名 → 正式名（全 JSON 内の "name" 文字列に再帰適用）
RENAME_EXACT: dict[str, str] = {
    "大腸": "コロン",
    "マンマイヤー・グンコ": "マンマイヤー・軍子宮",
    "マンマイヤー・ガンコ": "マンマイヤー・軍子宮",
    "ロイダー": "ロイド",
    "まだら": "マトラ",
}

data_to_process = {
    1176: {
        "title": "誇り高く",
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
            "ハイルディン",
            "ロキ",
            "シャンクス",
            "ラグニル",
        ],
        "cover": ["ヤマト"],
    },
    1177: {
        "title": "怒り",
        "normal": [
            "モンキー・D・ルフィ",
            "ロキ",
            "シャンクス",
            "ラグニル",
            "ラッキー・ルウ",
            "ヤソップ",
            "ベン・ベックマン",
        ],
        "cover": ["ヤマト"],
    },
    1178: {
        "title": "醒めてゆく悪夢",
        "normal": [
            "モンキー・D・ルフィ",
            "ロキ",
            "シャンクス",
            "リリス",
        ],
        "cover": ["ヤマト"],
    },
    1179: {
        "title": "ネロナ・イム降臨",
        "normal": [
            "ネロナ・イム",
            "フィガーランド・ガーリング",
            "マンマイヤー・軍子宮",
            "フィガーランド・シャムロック",
            "シェパード・十・ピーター",
            "マーカス・マーズ",
            "トップマン・ワルキュリー",
            "エサンバロン・V・ヌスジュロ",
        ],
        "cover": ["ヤマト"],
    },
    1180: {
        "title": "魔気（オーメン）",
        "normal": [
            "モンキー・D・ルフィ",
            "ロキ",
            "シャンクス",
            "エメト",
        ],
        "cover": ["ヤマト"],
    },
    1181: {
        "title": "神と悪魔",
        "normal": [
            "モンキー・D・ルフィ",
            "ロキ",
            "シャンクス",
            "ネロナ・イム",
        ],
        "cover": ["ヤマト"],
    },
}

SYNONYMS: dict[str, str] = {
    "ジャガー・D・サウロ": "ハグワール・D・サウロ",
    "ジャガー・D・ソール": "ハグワール・D・サウロ",
    "ジャガー_D_サウロ": "ハグワール・D・サウロ",
    "スコッパー・ギャバン": "ギャバン",
    "スコーパー・ガバン": "ギャバン",
    "スコーパー・ギャバン": "ギャバン",
    "ネロナ・イム": "イム",
    "シキ": "金獅子",
    "式": "金獅子",
    "シャーロット・リンリン": "ビッグ・マム",
    "ジェイガルシア・サターン": "ジェイガルシア・サターン聖",
    "トップマン・ワルキュリー": "トップマン・ウォーキュリー",
    "トップマン・ワルクリー": "トップマン・ウォーキュリー",
    "エサンバロン・V・ヌスジュロ": "イーザンバロン・V・ナス寿郎",
    "エサンバロン・V_ヌスジュロ": "イーザンバロン・V・ナス寿郎",
    "グロリオサ": "グロリオーサ",
    "ゼウス": "ゼウス・ブリーズテンポ",
    "菊之丞": "菊",
    "バルトロメオ・クマ": "バーソロミュー・くま",
    "バーソロミュー・クマ": "バーソロミュー・くま",
    "ユ・ペテロ": "シェパード・十・ピーター",
    "羊飼いユ・ペテロ": "シェパード・十・ピーター",
    "シェパード・ユ・ペテロ": "シェパード・十・ピーター",
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
    "甚平": "ジンベエ",
    "トニー・トニー・チョッパー": "トニートニー・チョッパー",
    "樫井": "カーシー",
    "ベンサム": "ボン・クレー",
    "曲がった": "マガッタ",
    "ラグニール": "ラグニル",
    "マンマイヤー・ガンコ": "マンマイヤー・軍子宮",
    "マンマイヤー・グンコ": "マンマイヤー・軍子宮",
    "アンジュ": "アンジェ",
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
    dotted = list_name.replace("_", "・")
    resolved = SYNONYMS.get(list_name, dotted)
    if resolved == dotted and dotted in SYNONYMS:
        resolved = SYNONYMS[dotted]
    keys: set[str] = set()
    for base in {list_name, resolved, dotted}:
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
    dotted = list_name.replace("_", "・")
    if list_name in SYNONYMS:
        return SYNONYMS[list_name]
    if dotted in SYNONYMS:
        return SYNONYMS[dotted]
    return dotted


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


def rename_all_name_fields(obj: object) -> None:
    """任意のネストで key=='name' の文字列を RENAME_EXACT に従い置換。"""
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if k == "name" and isinstance(v, str) and v in RENAME_EXACT:
                obj[k] = RENAME_EXACT[v]
            else:
                rename_all_name_fields(v)
    elif isinstance(obj, list):
        for item in obj:
            rename_all_name_fields(item)


def fix_appearance_titles(obj: object) -> None:
    """appearances / covers の title 内に誤字が混入していた場合の救済。"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in ("appearances", "covers") and isinstance(v, list):
                for entry in v:
                    if isinstance(entry, dict):
                        t = entry.get("title")
                        if isinstance(t, str) and "大腸" in t:
                            entry["title"] = t.replace("大腸", "コロン")
            else:
                fix_appearance_titles(v)
    elif isinstance(obj, list):
        for item in obj:
            fix_appearance_titles(item)


def run_final_update() -> None:
    with CHAR_PATH.open(encoding="utf-8") as f:
        chars: list[dict] = json.load(f)

    rename_all_name_fields(chars)
    fix_appearance_titles(chars)

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
        "✅ 名寄せリネーム（大腸→コロン 等）と 1176〜1181 反映が完了しました。"
        f" appearances 追加: {updated_app} / covers 追加: {updated_cov} / 新規: {new_n}"
    )


if __name__ == "__main__":
    run_final_update()
