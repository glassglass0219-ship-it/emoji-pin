"""
characters.json の alias を alias_map に基づき一括更新する。
名前比較は「・」を除いた正規化で行う（マッハ・バイス ↔ マッハバイス 等）。
"""

from __future__ import annotations

import json
import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.abspath(__file__))
CHAR_PATH = os.path.join(ROOT, "src", "data", "characters.json")

alias_map = {
    "トレーボル": "トレーボル軍 特別幹部",
    "ディアマンテ": "ディアマンテ軍 最高幹部",
    "ピーカ": "ピーカ軍 最高幹部",
    "ヴェルゴ": "鬼竹のヴェルゴ",
    "セニョール・ピンク": "ハードボイルド",
    "マッハバイス": "重量挙げチャンピオン",
    "デリンジャー": "闘魚の血",
    "ラオG": "地翁拳の使い手",
    "シュガー": "ホビホビの能力者",
    "キャベンディッシュ": "白馬",
    "バルトロメオ": "人食い",
    "ドン・チンジャオ": "錐のチンジャオ",
    "サイ": "八宝水軍13代棟梁",
    "ハック": "魚人空手師範代",
    "イデオ": "破壊砲",
    "ブルー・ギリー": "足長族の戦士",
    "モンキー・D・ドラゴン": "世界最悪の犯罪者",
    "サボ": "革命軍参謀総長 / 火拳",
    "エンポリオ・イワンコフ": "奇跡の人",
    "イナズマ": "閃電",
    "ベロ・ベティ": "東軍軍隊長",
    "モーリー": "西軍軍隊長",
    "カラス": "北軍軍隊長",
    "リンドバーグ": "南軍軍隊長",
    "ロブ・ルッチ": "殺し屋",
    "カク": "六式使い",
    "ジャブラ": "狼男",
    "ブルーノ": "扉の男",
    "スパンダム": "CP9長官",
    "ステューシー": "歓楽街の女王",
    "錦えもん": "狐火の錦えもん",
    "傳ジロー": "狂死郎",
    "菊之丞": "残雪の菊之丞",
    "雷ぞう": "霧の雷ぞう",
    "河松": "横綱河松",
    "アシュラ童子": "酒天丸",
    "うるティ": "頭突きのうるティ",
    "ページワン": "スピノサウルス",
    "ササキ": "装甲部隊長",
    "フーズ・フー": "元CP9",
    "ブラックマリア": "花魁蜘蛛",
    "ドレーク": "赤旗",
    "オロチ": "将軍",
    "カン十郎": "夕立ちカン十郎",
    "ヤマト": "鬼姫",
}

# JSON 側の別表記（ユーザー辞書のキーと正規化一致しないもの）
SYNONYMS = {
    "チンジャオ": "錐のチンジャオ",
    "菊": "残雪の菊之丞",
    "小紫": "残雪の菊之丞",
    "酒天丸": "酒天丸",
    "X・ドレーク": "赤旗",
}


def normalize_name(name: str | None) -> str:
    if not name:
        return ""
    s = str(name).strip()
    s = s.replace("・", "")
    s = s.replace(" ", "").replace("\u3000", "")
    return s


def to_alias_string(val) -> str:
    if isinstance(val, (list, tuple)):
        return " / ".join(str(x).strip() for x in val if str(x).strip())
    if val is None:
        return ""
    return str(val).strip()


def is_main_character(obj: dict) -> bool:
    return isinstance(obj, dict) and "firstAppearance" in obj and "appearances" in obj


def main() -> None:
    merged: dict[str, str] = {}
    for k, v in alias_map.items():
        merged[k] = to_alias_string(v)
    for k, v in SYNONYMS.items():
        merged.setdefault(k, to_alias_string(v))

    norm_to_alias: dict[str, str] = {}
    for canon_name, val in merged.items():
        kn = normalize_name(canon_name)
        if kn:
            norm_to_alias[kn] = to_alias_string(val)

    with open(CHAR_PATH, "r", encoding="utf-8") as f:
        chars: list = json.load(f)

    updated = 0
    for c in chars:
        if not is_main_character(c):
            continue
        nm = c.get("name")
        kn = normalize_name(nm)
        if kn in norm_to_alias:
            c["alias"] = norm_to_alias[kn]
            updated += 1

    with open(CHAR_PATH, "w", encoding="utf-8") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)

    print(f"異名を更新したキャラクター数: {updated}", flush=True)


if __name__ == "__main__":
    main()
