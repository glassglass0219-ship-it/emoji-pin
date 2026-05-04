#!/usr/bin/env python3
"""1115話以降の正式タイトルを manga_anime_map.json と characters.json に反映する。"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MAP_PATH = ROOT / "src" / "data" / "manga_anime_map.json"
CHARS_PATH = ROOT / "src" / "data" / "characters.json"

OFFICIAL_TITLES = {
    1115: "大陸の断片",
    1116: "葛藤",
    1117: "も",
    1118: "自由になる",
    1119: "エメト",
    1120: "暴（アトラス）",
    1121: "時代のうねり",
    1122: "イザッテトキ",
    1123: "空白の2週間",
    1124: "親友",
    1125: "何をもって死とするか",
    1126: "落とし前",
    1127: "謎の国の冒険",
    1128: "RPG",
    1129: "生人形（リドール）",
    1130: "呪いの王子",
    1131: "冥界のロキ",
    1132: "エルバフの冒険",
    1133: "褒めてほしい",
    1134: "フクロウの図書館",
    1135: "友の盃",
    1136: "太陽を待つ国",
    1137: "シャムロック登場",
    1138: "神典（ハーレイ）",
    1139: "山喰らい",
    1140: "スコッパー・ギャバン",
    1141: "歳上の女",
    1142: "わたしのこわいもの",
    1143: "神の騎士団",
    1144: "戦士の時間",
    1145: "樹道8号線第2樹林区火災",
    1146: "静中に動あり",
    1147: "我々の恐いもの",
    1148: "ローニャ",
    1149: "一秒",
    1150: "黒転支配（ドミ・リバーシ）",
    1151: "もういいわかった!!!",
    1152: "ヒドい一日",
    1153: "ロキ誕生",
    1154: "死ねもしねェ",
    1155: "ロックス海賊団",
    1156: "アイドル",
    1157: "伝説のBAR",
    1158: "ロックスvs.ハラルド",
    1159: "運命の島",
    1160: "ゴッドバレー事件",
    1161: "矢の雨をしのいで結ぶ恋の詩",
    1162: "Ｇ・Ｖ・Ｂ・Ｒ（ゴッドバレーバトルロワイヤル）",
    1163: "約束",
    1164: "デービーの血",
    1165: "残響",
    1166: "新しい物語",
    1168: "エルバフの雪",
    1169: "一刻も早く死ななくては",
    1170: "裏腹",
    1171: "鉄雷（ラグニル）",
    1172: "おれの憧れたエルバフ",
    1173: "戦士の世代",
    1174: "せかいで１番つよいもの",
    1175: "雷竜（ニーズホッグ）",
    1176: "誇り高く",
    1177: "怒り",
    1178: "醒めてゆく悪夢",
    1179: "ネロナ・イム降臨",
    1180: "魔気（オーメン）",
    1181: "神と悪魔",
}


def main() -> None:
    with MAP_PATH.open(encoding="utf-8") as f:
        manga_map = json.load(f)

    map_updated = 0
    map_added = 0
    for ep, title in OFFICIAL_TITLES.items():
        key = str(ep)
        if key in manga_map:
            entry = manga_map[key]
            if isinstance(entry, dict):
                manga_map[key] = {**entry, "title": title}
            else:
                # レガシー: 数値のみなど
                manga_map[key] = {"ep": entry, "title": title}
            map_updated += 1
        else:
            manga_map[key] = {"title": title}
            map_added += 1

    with MAP_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(manga_map, f, ensure_ascii=False, indent=2)
        f.write("\n")

    with CHARS_PATH.open(encoding="utf-8") as f:
        characters = json.load(f)

    app_replaced = 0
    for char in characters:
        apps = char.get("appearances")
        if not isinstance(apps, list):
            continue
        for row in apps:
            if not isinstance(row, dict):
                continue
            ep = row.get("episode")
            try:
                ep_int = int(ep)
            except (TypeError, ValueError):
                continue
            if ep_int in OFFICIAL_TITLES:
                row["title"] = OFFICIAL_TITLES[ep_int]
                app_replaced += 1

    with CHARS_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(characters, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(
        f"manga_anime_map: {map_updated} entries merged title, {map_added} new keys; "
        f"characters: {app_replaced} appearance titles updated."
    )


if __name__ == "__main__":
    main()
