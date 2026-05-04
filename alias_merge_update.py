"""
final_alias_map に基づき characters.json の alias を補完・統合する。
マッチしないキーは明示オーバーライドで解決し、それでも無ければ新規キャラを末尾に追加。

  python alias_merge_update.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import unicodedata

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.abspath(__file__))
CHAR_PATH = os.path.join(ROOT, "src", "data", "characters.json")

FINAL_ALIAS_MAP: dict[str, str] = {
    "ポートガス・D・エース": "火拳",
    "サッチ": "4番隊隊長",
    "ブレンハイム": "隊長",
    "ラクヨウ": "隊長",
    "ナミュール": "魚人隊長",
    "クリエル": "隊長",
    "フォッサ": "隊長",
    "スコッパー・ギャバン": "左腕",
    "クロッカス": "灯台守",
    "ミス・オールサンデー": "ニコ・ロビン",
    "ミスター1": "ダズ・ボーネス",
    "ミス・ダブルフィンガー": "ザラ",
    "ミスター2": "ボン・クレー",
    "ミスター3": "ギャルディーノ",
    "ミス・ゴールデンウィーク": "マリアンヌ",
    "カリファ": "秘書",
    "クマドリ": "歌舞伎役者",
    "フクロウ": "チャパパ",
    "コニス": "空島の少女",
    "パガヤ": "住民",
    "アイサ": "心綱の少女",
    "ネプチューン": "海王",
    "しらほし": "人魚姫",
    "フカボシ": "王子",
    "リュウボシ": "王子",
    "マンボシ": "王子",
    "キュロス": "片足の兵隊",
    "リク王": "前国王",
    "ガンビア": "参謀",
    "お玉": "くノ一見習い",
    "トコ": "えびす町",
    "ヒョウ五郎": "花のヒョウ五郎",
    "オニ丸": "牛鬼",
    "Tボーン": "船斬り",
    "シュウ": "サビサビ",
    "ベリーグッド": "ベリベリ",
    "ストロベリー": "中将",
    "オニグモ": "中将",
    "モンブラン・ノーランド": "大うそつき",
    "カルガラ": "戦士",
    "ノジコ": "姉",
    "ガイモン": "宝箱男",
}

# リストのキー → JSON 上の name（表記揺れ・別名）
KEY_TO_JSON_NAME: dict[str, str] = {
    "ミスター1": "Mr.1",
    "ミスター2": "ボン・クレー",
    "ミスター3": "Mr.3",
    "ミス・オールサンデー": "ニコ・ロビン",
    "リク王": "リク・ドルド",
    "ヒョウ五郎": "ヒョウじい",
}


def loose_norm(s: str) -> str:
    u = unicodedata.normalize("NFKC", (s or "").strip())
    u = u.replace("・", "").replace(" ", "").replace("　", "").replace(".", "")
    u = "".join(c.lower() if c.isascii() and c.isalpha() else c for c in u)
    u = u.replace("ミスター", "mr").replace("ミス", "miss")
    return u


def merge_alias(old: str, new_part: str) -> str:
    new_part = (new_part or "").strip()
    if not new_part:
        return (old or "").strip()
    parts = [p.strip() for p in (old or "").split("、") if p.strip()]
    if new_part not in parts:
        parts.append(new_part)
    return "、".join(parts)


def blank_character(name: str, cid: int, alias: str) -> dict:
    return {
        "id": cid,
        "name": name,
        "reading": "",
        "gender": "",
        "affiliation": "",
        "devilFruit": "",
        "bounty": "",
        "birthday": "",
        "firstAppearance": 0,
        "appearances": [],
        "abilities": [],
        "coAppearances": [],
        "alias": alias,
    }


def main() -> None:
    with open(CHAR_PATH, "r", encoding="utf-8") as f:
        chars: list[dict] = json.load(f)

    exact: dict[str, dict] = {}
    for c in chars:
        nm = str(c.get("name", "")).strip()
        if nm and nm not in exact:
            exact[nm] = c

    loose_to_char: dict[str, dict] = {}
    for c in chars:
        nm = str(c.get("name", "")).strip()
        if not nm:
            continue
        lk = loose_norm(nm)
        if lk not in loose_to_char:
            loose_to_char[lk] = c

    max_id = max((int(c["id"]) for c in chars if isinstance(c.get("id"), int)), default=0)

    updated = 0
    added = 0
    skipped: list[str] = []

    for map_key, alias_val in FINAL_ALIAS_MAP.items():
        target_name = KEY_TO_JSON_NAME.get(map_key, map_key)
        char = exact.get(target_name)
        if not char:
            char = loose_to_char.get(loose_norm(target_name))
        if not char:
            nk = loose_norm(map_key)
            char = loose_to_char.get(nk)
        if not char:
            # 部分一致（一意のときのみ）
            cands = [
                c
                for c in chars
                if nk and (nk in loose_norm(str(c.get("name", ""))) or loose_norm(str(c.get("name", ""))) in nk)
            ]
            if len(cands) == 1:
                char = cands[0]
        if not char:
            new_id = max_id + 1
            max_id = new_id
            chars.append(blank_character(map_key, new_id, alias_val.strip()))
            added += 1
            print(f"[新規] id={new_id} name={map_key!r} alias={alias_val!r}")
            exact[map_key] = chars[-1]
            loose_to_char[loose_norm(map_key)] = chars[-1]
            continue

        old_a = str(char.get("alias", "") or "")
        new_a = merge_alias(old_a, alias_val)
        if new_a != old_a:
            char["alias"] = new_a
            updated += 1
            print(f"[更新] {char.get('name')!r}: {old_a!r} → {new_a!r}")
        else:
            skipped.append(map_key)

    with open(CHAR_PATH, "w", encoding="utf-8") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)

    print(
        f"\n完了: alias を変更したキャラ {updated} 件、新規追加 {added} 件。"
        f"（変更なしキー: {len(skipped)}）"
    )
    if skipped:
        print("変更なし例:", "、".join(skipped[:12]) + ("…" if len(skipped) > 12 else ""))


if __name__ == "__main__":
    main()
