"""
skills.json の空欄 reading を、ONE PIECE 原作寄りの固有名置換 + pykakasi で一括補完します。

  pip install pykakasi
  python skill_enricher.py
"""

from __future__ import annotations

import json
import os
import re
import sys

JSON_PATH = "src/data/skills.json"

# 「漢字部分 → 読み（カタカナ／ひらがな）」長いパターンを先に列挙
_PHRASE_LINES = """
犀榴弾砲|リノシュナイダー
大蛇砲|カルヴァリン
猿神銃|バジュラングガン
猿王銃|コングガン
大猿王銃|キングコングガン
業火拳銃|レッドロック
火拳銃|レッドホーク
灰熊銃|グリズリーマグナム
象銃|エレファントガン
黄金銃|ゴールデンピストル
怪鳥銃|ロックガン
銃乱打|ガトリング
銃弾|ブレット
獅子・バズーカ|レオ・バズーカ
獅子バズーカ|レオ・バズーカ
鬼斬り|おにぎり
虎狩り|とらがかり
三千世界|さんぜんせかい
獅子歌歌|ししそんそん
煩悩鳳|ポンドほう
鴉魔狩り|からすまがり
羅生門|らしょうもん
剛力斬|にごりざけ
豹琴玉|ひょうきんだま
阿修羅 弌霧銀|あしゅら いちぶぎん
阿修羅|あしゅら
弌霧銀|いちぶぎん
煉獄|れんごく
極虎狩|きょくこがり
一大三千大千世界|いちだいさんぜんだいせんせかい
飛龍侍極|ひりゅうじごく
首肉|コリエ
肩肉|エポール
背肉|ロワン
鞍下肉|ロニニ
胸肉|ポワトリーヌ
腹肉|フランシェ
もも肉|ジゴ
仔牛肉|ヴォー
羊肉|ムートン
粗砕|コンカッセ
整形|パラージュ
画竜点睛|フランバージュ
悪魔風脚|ディアブルジャンブ
焼鉄鍋|ポアル・ア・フリール
魔神風脚|イフリートジャンブ
輪咲き|フルール
蜘蛛の華|スパイダーネット
巨大樹|ヒガンテ・フルール
悪魔咲き|デモニオ・フルール
衝撃波動|ショックヴィレ
穿刺波動|パンクチャーヴィレ
麻酔|アネスティシア
抗菌武装|カーテン
熱息|ボロブレス
壊風|カイフウ
降三世引奈落|ラグナラク
咆雷八卦|ほうらいはっけ
雷鳴八卦|らいめいはっけ
軍茶利龍盛軍|ぐんだりりゅうせいぐん
鳴鏑|なりかぶら
神避|かむさり
黒い蛇群|ブラックマンバ
戦斧|アックス
風車|かざぐるま
鐘|ベル
網|ネット
盾|シールド
鎌|カマ
槍|スピア
槌|ハンマー
鞭|ウィップ
斧|アックス
弾|バレット
鷹|ホーク
鷲|イーグル
白い|ドーン
銃|ピストル
"""

# ゴムゴム系など「の」の直後だけ銃→ピストルにしたいが、上の「銃」は広く当たる。
# 先に銃乱打・銃弾・黄金銃…を処理済みなので最後の「銃」は残りの銃（ピストル）向け


def _load_phrases() -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for line in _PHRASE_LINES.splitlines():
        line = line.strip()
        if not line or "|" not in line:
            continue
        a, b = line.split("|", 1)
        out.append((a.strip(), b.strip()))
    out.sort(key=lambda x: len(x[0]), reverse=True)
    return out


PHRASES = _load_phrases()


def _kakasi_to_katakana(text: str) -> str:
    try:
        from pykakasi import kakasi
    except ImportError:
        return text
    k = kakasi()
    parts: list[str] = []
    for seg in k.convert(text):
        parts.append(seg.get("kana") or seg.get("hira") or seg.get("orig", ""))
    return "".join(parts)


def enrich_reading(name: str) -> str:
    if not name or not name.strip():
        return ""
    s = name
    for pat, yomi in PHRASES:
        if pat in s:
            s = s.replace(pat, yomi)
    # 記号・英数・カタカナ・ひらがな・漢字の混在を pykakasi で読みに寄せる
    kata = _kakasi_to_katakana(s)
    # 変化が無く pykakasi も効かない場合は、置換後の表記をそのまま返す（漢字のまま可）
    return (kata or s).strip()


def main() -> None:
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    if not os.path.isfile(JSON_PATH):
        print(f"Error: {JSON_PATH} not found")
        sys.exit(1)

    with open(JSON_PATH, encoding="utf-8") as f:
        skills: list = json.load(f)

    updated = 0
    for skill in skills:
        if not isinstance(skill, dict):
            continue
        cur = skill.get("reading", "")
        if isinstance(cur, str) and cur.strip():
            continue
        name = skill.get("name") or ""
        new_r = enrich_reading(name)
        if not new_r:
            continue
        skill["reading"] = new_r
        updated += 1

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(skills, f, ensure_ascii=False, indent=2)

    print(f"reading を更新した件数: {updated} / {len(skills)}")


if __name__ == "__main__":
    main()
