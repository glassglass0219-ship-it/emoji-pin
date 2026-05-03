import json
import os

JSON_PATH = "src/data/skills.json"

# 特に検索されそうな、漢字と読みが乖離している技のリスト
# ここに書き足すことで、検索エンジンをどんどん賢くできます
SPECIAL_READINGS = {
    "猿王銃": "コングガン",
    "大猿王銃": "キングコングガン",
    "猿神銃": "バジュラングガン",
    "犀榴弾砲": "リノシュナイダー",
    "大蛇砲": "カルヴァリン",
    "黒い蛇群": "ブラックマンバ",
    "業火拳銃": "レッドロック",
    "火拳銃": "レッドホーク",
    "灰熊銃": "グリズリーマグナム",
    "象銃": "エレファントガン",
    "鳴鏑": "なりかぶら",
    "神避": "かむさり",
    "咆雷八卦": "ほうらいはっけ",
    "雷鳴八卦": "らいめいはっけ",
    "降三世引奈落": "こうさんぜらぐならく",
    "軍茶利龍盛軍": "ぐんだりりゅうせいぐん",
    "獅子歌歌": "ししそんそん",
    "一大三千大千世界": "いちだいさんぜんだいせんせかい",
}

def update_skills():
    if not os.path.exists(JSON_PATH):
        print("❌ skills.json が見つかりません。")
        return

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        skills = json.load(f)

    updated_count = 0
    for skill in skills:
        name = skill.get("name", "")
        # 特殊読みリストにある漢字が技名に含まれているかチェック
        for kanji, reading in SPECIAL_READINGS.items():
            if kanji in name:
                # 既存の読み(reading)を強化する
                current_reading = skill.get("reading", "")
                if reading not in current_reading:
                    skill["reading"] = f"{current_reading} {reading}".strip()
                    updated_count += 1

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(skills, f, ensure_ascii=False, indent=2)

    print(f"✨ {updated_count} 件の技の読み方をアップデートしました！")

if __name__ == "__main__":
    update_skills()