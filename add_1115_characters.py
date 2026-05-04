#!/usr/bin/env python3
"""第1115話の登場キャラを characters.json に反映する（既存は appearances 追記、未登録は新規）。"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAR_PATH = ROOT / "src/data/characters.json"
EP_NUM = 1115
EP_TITLE = "大陸の断片"

char_list_1115 = [
    "モンキー・D・ルフィ",
    "ロロノア・ゾロ",
    "ナミ",
    "ウソップ",
    "サンジ",
    "フランキー",
    "ジンベエ",
    "ジュエリー・ボニー",
    "ドリー",
    "ブロギー",
    "オイモ",
    "カーシー",
    "デマロ・ブラック",
    "マンジャロ",
    "ドタ",
    "トゥルコ",
    "フォクシー",
    "ポルシェ",
    "ハンブルク",
    "ロシオ",
    "ジョイボーイ",
    "ネロナ・イム",
    "ジェイガルシア・サターン",
    "マーカス・マーズ",
    "トップマン・ワルキュリー",
    "エサンバロン・V・ヌスジュロ",
    "カク",
    "S-ホーク",
    "S-スネーク",
    "S-シャーク",
    "S-ベア",
    "モンキー・D・ドラゴン",
    "サボ",
    "エンポリオ・イワンコフ",
    "モーリー",
    "ベロ・ベティ",
    "コアラ",
    "ガンボ",
    "ベガパンク",
    "エジソン",
    "シモツキ・コウシロウ",
    "ゲンゾウ",
    "ノジコ",
    "ナコ",
    "チャボ",
    "ダルトン",
    "ドクトリーヌ・くれは",
    "ネフェルタリ・ビビ",
    "ワポル",
    "マリアンヌ",
    "ミス・メリークリスマス",
    "ミス・バレンタイン",
    "ニンジン",
    "ワンダ",
    "シシリアン",
    "コンセロット",
    "ジョヴァンニ",
    "ヨモ",
    "ズニーシャ",
    "光月モモの助",
    "錦えもん",
    "お玉",
    "しのぶ",
    "ヤマト",
    "光月日和",
    "トコ",
    "ステューシー",
    "アイアン・ジャイアント",
    "モルガンズ",
]

# リスト表記と JSON 上の表記の差を吸収（新規作成時の名前もここを優先）
SYNONYMS: dict[str, str] = {
    "ドタ": "ドリップ",
    "トゥルコ": "トルコ",
    "トップマン・ワルキュリー": "トップマン・ウォーキュリー",
    "エサンバロン・V・ヌスジュロ": "イーザンバロン・V・ナス寿郎",
    "ネロナ・イム": "イム",
    "ニンジン": "キャロット",
    "ハンブルク": "ハンバーグ",
    "ポルシェ": "ポルチェ",
    "ガンボ": "ギャンボ",
    "ドクトリーヌ・くれは": "くれは",
    "マリアンヌ": "ミス・ゴールデンウィーク",
    "ジョヴァンニ": "ジョバンニ",
    "光月日和": "小紫",
}


def norm_key(s: str) -> str:
    t = re.sub(r"[・\s]", "", (s or "").strip())
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


def new_character_stub(char_id: int, list_name: str) -> dict:
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
        "firstAppearance": EP_NUM,
        "appearances": [{"episode": EP_NUM, "title": EP_TITLE}],
    }


def run_update() -> None:
    with CHAR_PATH.open(encoding="utf-8") as f:
        chars: list[dict] = json.load(f)

    next_id = max(int(c["id"]) for c in chars) + 1
    updated_count = 0
    new_count = 0

    for list_name in char_list_1115:
        target = find_character(chars, list_name)

        if target is not None:
            apps = target.setdefault("appearances", [])
            if not isinstance(apps, list):
                continue
            has_ep = False
            for a in apps:
                if not isinstance(a, dict):
                    continue
                try:
                    if int(a.get("episode")) == EP_NUM:
                        has_ep = True
                        break
                except (TypeError, ValueError):
                    continue
            if not has_ep:
                apps.append({"episode": EP_NUM, "title": EP_TITLE})

                def _ep_key(x: dict) -> int:
                    try:
                        return int(x.get("episode"))
                    except (TypeError, ValueError):
                        return 0

                apps.sort(key=_ep_key)
                updated_count += 1
        else:
            chars.append(new_character_stub(next_id, list_name))
            print(f"[NEW] {storage_name(list_name)} (id={next_id})")
            next_id += 1
            new_count += 1

    chars.sort(key=lambda x: int(x["id"]))

    with CHAR_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"完了。既存に登場追加: {updated_count} 名 / 新規: {new_count} 名")


if __name__ == "__main__":
    run_update()
