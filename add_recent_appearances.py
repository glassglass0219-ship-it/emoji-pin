#!/usr/bin/env python3
"""1116〜1118話の登場キャラを characters.json に一括反映する。"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAR_PATH = ROOT / "src/data/characters.json"

data_to_add = {
    1116: {
        "title": "葛藤",
        "chars": [
            "クロコダイル",
            "ネロナ・イム",
            "ジェイガルシア・サターン",
            "マーカス・マーズ",
            "エサンバロン・V・ヌスジュロ",
            "シェパード・十・ピーター",
            "サカズキ",
            "つる",
            "コーミル",
            "センゴク",
            "カク",
            "ヨーク",
            "S-スネーク",
            "ベガパンク",
            "エジソン",
            "ネフェルタリ・D・リリィ",
            "ネフェルタリ・コブラ",
            "ネフェルタリ・ビビ",
            "イガラム",
            "チャカ",
            "ペル",
            "カルー",
            "コーザ",
            "トト",
            "エリック",
            "ウサッコフ",
            "エリザベロー2世",
            "ダガマ",
            "光月モモの助",
            "錦えもん",
            "お玉",
            "ヤマト",
            "お鶴",
            "浦島",
            "ネプチューン",
            "しらほし",
            "左大臣",
            "右大臣",
            "ホーディ・ジョーンズ",
            "クロッカス",
            "ラブーン",
            "サンクリン",
            "シルバーズ・レイリー",
            "シャッキー",
            "ジロン",
            "あひる",
            "牛野",
            "モーダ",
            "ステューシー",
            "アイアン・ジャイアント",
        ],
    },
    1117: {
        "title": "も",
        "chars": [
            "モンキー・D・ルフィ",
            "ロロノア・ゾロ",
            "ナミ",
            "ウソップ",
            "サンジ",
            "トニートニー・チョッパー",
            "ブルック",
            "ジンベエ",
            "ジュエリー・ボニー",
            "ドリー",
            "ブロギー",
            "オイモ",
            "カーシー",
            "トルマン",
            "ドン・クリーク",
            "ギン",
            "パール",
            "モンブラン・クリケット",
            "マシラ",
            "ショウジョウ",
            "マーシャル・D・ティーチ",
            "ベポ",
            "ジェイガルシア・サターン",
            "マーカス・マーズ",
            "トップマン・ワルキュリー",
            "エサンバロン・V・ヌスジュロ",
            "シェパード・十・ピーター",
            "スモーカー",
            "ハウンド",
            "ブルーグラス",
            "X・ドレーク",
            "プリンス・グルス",
            "コビー",
            "ひばり",
            "ヘルメッポ",
            "ヨーク",
            "ベガパンク",
            "リリス",
            "アトラス",
            "メロ",
            "ネフェルタリ・ビビ",
            "ワポル",
            "ヤマト",
            "ネコマムシ",
            "ヒョウ五郎",
            "モンキー・D・ドラゴン",
            "サボ",
            "アイアン・ジャイアント",
            "モルガンズ",
        ],
    },
    1118: {
        "title": "自由になる",
        "chars": [
            "モンキー・D・ルフィ",
            "ナミ",
            "ウソップ",
            "サンジ",
            "フランキー",
            "ジュエリー・ボニー",
            "ドリー",
            "ブロギー",
            "オイモ",
            "カーシー",
            "ビョルン",
            "シグ",
            "レオ",
            "ジェイガルシア・サターン",
            "マーカス・マーズ",
            "トップマン・ワルキュリー",
            "エサンバロン・V・ヌスジュロ",
            "シェパード・十・ピーター",
            "ブルーグラス",
            "ヨーク",
            "リリス",
            "アトラス",
            "コーザ",
            "トト",
            "エリック",
            "カッパ",
            "ミスター9",
            "ミス・マンデー",
            "ミス・ゴールデンウィーク",
            "ナンデー",
            "レベッカ",
            "ヤマト",
            "バーソロミュー・くま",
            "アイアン・ジャイアント",
        ],
    },
}

SYNONYMS: dict[str, str] = {
    "ネロナ・イム": "イム",
    "エサンバロン・V・ヌスジュロ": "イーザンバロン・V・ナス寿郎",
    "トップマン・ワルキュリー": "トップマン・ウォーキュリー",
    "光月モモの助": "モモの助",
    "エリザベロー2世": "エリザベロー",
    "ミスター9": "Mr.9",
    "シャッキー": "シャクヤク",
    "ドン・クリーク": "クリーク",
}


def norm_key(s: str) -> str:
    t = re.sub(r"[・\s\-]", "", (s or "").strip())
    while len(t) > 1 and t.endswith("聖"):
        t = t[:-1]
    return t


def variant_keys(list_name: str) -> set[str]:
    resolved = SYNONYMS.get(list_name, list_name)
    keys: set[str] = set()
    for base in {list_name, resolved}:
        if not base:
            continue
        keys.add(norm_key(base))
        if base.startswith("光月") and len(base) > 2:
            keys.add(norm_key(base[2:]))
    return keys


def find_character(chars: list[dict], list_name: str) -> dict | None:
    keys = variant_keys(list_name)
    for c in chars:
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
    return SYNONYMS.get(list_name, list_name)


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

    next_id = max(int(c["id"]) for c in chars) + 1
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

    print(f"完了。既存へ登場追加: {updated} 件 / 新規キャラ: {new_n} 件")


if __name__ == "__main__":
    run_update()
