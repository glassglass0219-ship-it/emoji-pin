#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path


def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "").strip())


_SPACE_RE = re.compile(r"[ \t\u3000]+")


def norm_name(s: str) -> str:
    t = nfkc(s)
    t = _SPACE_RE.sub("", t)
    t = t.lower()
    for ch in ["・", "･", "“", "”", "〝", "〟", "「", "」", "『", "』", "｢", "｣"]:
        t = t.replace(ch, "")
    return t


def ensure_list(v: object) -> list[str]:
    if isinstance(v, list):
        out: list[str] = []
        seen: set[str] = set()
        for x in v:
            if not isinstance(x, str):
                continue
            t = x.strip()
            if not t or t in seen:
                continue
            seen.add(t)
            out.append(t)
        return out
    if isinstance(v, str):
        t = v.strip()
        return [t] if t else []
    return []


def main() -> int:
    category_to_add = "海賊"
    targets = [
        "モンキー・Ｄ・ルフィ",
        "ロロノア・ゾロ",
        "ナミ",
        "ウソップ",
        "サンジ",
        "トニートニー・チョッパー",
        "ニコ・ロビン",
        "フランキー（カティ・フラム）",
        "ブルック",
        "ジンベエ",
        "ゴーイング・メリー号",
        "サウザンド・サニー号",
        "ネフェルタリ・ビビ",
        "ゴール・Ｄ・ロジャー",
        "モンスター",
        "シャンクス",
        "ラッキー・ルウ",
        "ヤソップ",
        "ベン・ベックマン",
        "アルビダ",
        "ヘッポコ",
        "ペッポコ",
        "ポッポコ",
        "綱渡りフナンボローズ",
        "怪力ドミンゴス",
        "バギー",
        "軽業フワーズ",
        "モージ",
        "リッチー",
        "カバジ",
        "クロ（クラハドール）",
        "シャム",
        "ブチ",
        "ヌギレ・ヤイヌ",
        "ギン",
        "クリーク",
        "ジュラキュール・ミホーク",
        "パール",
        "アイデアマン",
        "ハッスル",
        "カギッコ",
        "アーロン",
        "カネシロ",
        "ピサロ",
        "モーム",
        "チュウ",
        "クロオビ",
        "シオヤキ",
        "タケ",
        "パッキー",
        "コゼ",
        "ラブーン",
        "クロッカス",
        "カルー",
        "ブロギー",
        "ドリー",
        "ギャルディーノ（Mr.3）",
        "チェス",
        "クロマーリモ",
        "ユリカー",
        "プップー",
        "クロコダイル",
        "ポートガス・D・エース",
        "ダズ・ボーネス（Mr.1）",
        "マシラ",
        "ロシオ",
        "ベラミー",
        "サーキース",
        "リリー",
        "リヴァーズ",
        "ロス",
        "エディ",
        "ヒューイット",
        "マニ",
        "ミュレ",
        "オコメ",
        "ウータンダイバーズ",
        "ショウジョウ",
        "モンブラン・クリケット",
        "ドンキホーテ・ドフラミンゴ",
        "バーソロミュー・くま",
        "ラフィット",
        "ロックスター",
        "エドワード・ニューゲート（白ひげ）",
        "テート",
        "ジーザス・バージェス",
        "ヴァン・オーガー",
        "マーシャル・D・ティーチ（黒ひげ）",
        "ドクQ",
        "ストロンガー",
        "ポルチェ",
        "フォクシー",
        "ハンバーグ",
        "キバガエル",
        "イトミミズ",
        "チュチューン",
        "カポーティ",
        "モンダ",
        "ピクルス",
        "ビッグパン",
        "マウンテンリッキー",
        "ジョージ・マッハ",
        "ソニエ",
        "ドノバン",
        "ジーナ",
        "クザン（青雉）",
        "ミカヅキ",
        "カーシー",
        "オイモ",
        "チェスキッパ",
        "マルコ",
        "ジョズ",
        "キャプテン・シーマーズ",
        "サッチ",
        "ケルベロス（ゾンビ）",
        "ヒルドン",
        "モクドナルド",
        "ユニガロ",
        "ビクトリア・シンドリー",
        "ホグバック",
        "ブヒチャック",
        "敷きグマ",
        "クマシー",
        "ニン",
        "ギョロ",
        "バオ",
        "アブサロム",
        "ペローナ",
        "キャプテン・ジョン",
        "シャーロット・ローラ",
        "リスキー兄弟",
        "犬ッペ",
        "ジゴロウ",
        "タララン",
        "スパイダーマウス",
        "ゲッコー・モリア",
        "オーズ",
        "カバ紳士",
        "キャプテン・グー",
        "ヨーキ",
        "ミズータ・マダイスキー",
        "ミズータ・マワリトスキー",
        "マクロ",
        "ギャロ",
        "タンスイ",
        "デビル・ディアス",
        "ジャンバール",
        "カイリケン",
        "ミノルバ",
        "カポネ・ベッジ",
        "ジュエリー・ボニー",
        "バジル・ホーキンス",
        "ユースタス・キッド",
        "スクラッチメン・アプー",
        "ウルージ",
        "キラー（鎌ぞう）",
        "トラファルガー・ロー（トラファルガー・Ｄ・ワーテル・ロー）",
        "ペンギン",
        "ベポ",
        "シャチ",
        "ヒート",
        "ワイヤー",
        "スタンセン",
        "シルバーズ・レイリー",
        "バイロン",
        "ラキューバ",
        "ファウスト",
        "キャンディー",
        "グロリオーサ（ニョン婆）",
        "遊蛇",
        "ラン",
        "コスモス",
        "リンドウ",
        "ブルーファン",
        "デージー",
        "ボア・ハンコック",
        "ボア・サンダーソニア",
        "ボア・マリーゴールド",
        "サロメ",
        "シリュウ",
        "スクアード",
        "プリンス・ベレット",
        "セイバー",
        "フィナモレ",
        "バリー",
        "キメル",
        "ドギャ",
        "クーカイ",
        "ナミュール",
        "ビスタ",
        "クリエル",
        "スピード・ジル",
        "ラクヨウ",
        "ブレンハイム",
        "フォッサ",
        "ハルタ",
        "ブラメンコ",
        "イゾウ",
        "アトモス",
        "リトルオーズJr.",
        "ドーマ",
        "マクガイ",
        "ディカルバン兄弟",
        "エルミー",
        "ランバ",
        "A・O",
        "デラクアヒ",
        "ゾディア",
        "パームス",
        "エポイダ",
        "カルマ",
        "キングデュー",
        "パブリク",
        "ヴィタン",
        "ビザール",
        "ケチャッチ",
    ]

    path = Path("src/data/characters.json")
    chars = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(chars, list):
        raise SystemExit("characters.json must be a list")

    idx: dict[str, list[dict]] = {}
    for c in chars:
        if not isinstance(c, dict):
            continue
        nm = str(c.get("name") or "")
        if nm:
            idx.setdefault(norm_name(nm), []).append(c)

    changed = 0
    skipped = 0
    missing: list[str] = []
    multi: list[tuple[str, list[int]]] = []

    for name in targets:
        bucket = idx.get(norm_name(name)) or []
        if not bucket:
            missing.append(name)
            continue
        if len(bucket) > 1:
            ids = sorted(int(x.get("id", 10**9)) for x in bucket)
            multi.append((name, ids))
        ch = min(bucket, key=lambda x: int(x.get("id", 10**9)))

        cats = ensure_list(ch.get("category"))
        if category_to_add in cats:
            skipped += 1
            continue
        cats.append(category_to_add)
        ch["category"] = cats
        changed += 1

    chars.sort(key=lambda x: int(x.get("id", 0)) if isinstance(x, dict) else 0)
    path.write_text(json.dumps(chars, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    print(f"category_added={category_to_add}")
    print(f"changed={changed}")
    print(f"skipped_already_had_category={skipped}")
    print(f"missing_count={len(missing)}")
    for m in missing:
        print(f"MISSING {m}")
    print(f"multi_hit_count={len(multi)}")
    for n, ids in multi[:50]:
        print(f"MULTI {n} ids={ids}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

