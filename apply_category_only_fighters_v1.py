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
    category_to_add = "戦う者達"
    targets = [
        "ヒグマ",
        "モーガン",
        "ガイモン",
        "ヨサク",
        "ジョニー",
        "ゼフ",
        "パティ",
        "カルネ",
        "はっちゃん",
        "ベルメール",
        "クロッカス",
        "Mr.9",
        "Mr.13",
        "ミス・フライデー",
        "ミス・キャサリーナ",
        "Mr.ビーンズ",
        "Mr.シミズ",
        "ミス・マンデー",
        "ジェム（Mr.5）",
        "ミキータ（ミス・バレンタイン）",
        "ギャルディーノ（Mr.3）",
        "マリアンヌ（ミス・ゴールデンウィーク）",
        "バナナワニ",
        "Mr.11",
        "アクマイ",
        "ベンサム（Mr.2・ボン・クレー）",
        "クロコダイル",
        "Mr.メロウ",
        "ドロフィー（ミス・メリークリスマス）",
        "ベーブ（Mr.4）",
        "ザラ（ミス・ダブルフィンガー）",
        "ダズ・ボーネス（Mr.1）",
        "バンチ",
        "エリマキランナーズ",
        "コーザ",
        "おかめ",
        "ナットー",
        "ケビ",
        "アゴトギ",
        "ファラフラ",
        "エリック",
        "コアラ組",
        "F-ワニ",
        "ラッスー",
        "Mr.7（元）",
        "ミス・ファーザーズデー",
        "Mr.7",
        "Mr.ラブ",
        "ジョボ",
        "ガン・フォール",
        "ピエール",
        "ホーリー",
        "マッキンリー",
        "サトリ",
        "フザ",
        "シュラ",
        "カマキリ",
        "ワイパー",
        "ゲンボウ",
        "ブラハム",
        "オーム",
        "ゲダツ",
        "ヤマ",
        "エネル",
        "ホトリ",
        "コトリ",
        "ヨツバネ",
        "マユシカ",
        "ワラシ",
        "シャンディアの酋長",
        "カルガラ",
        "モンブラン・ノーランド",
        "チヤ",
        "セト",
        "Dr.ホンナー",
        "コバーン",
        "クザン（青雉）",
        "ザンバイ",
        "ショルゾウ",
        "コップ",
        "タマゴン",
        "キエフ",
        "キウイ",
        "モズ",
        "ソドム",
        "ゴモラ",
        "ダゴ",
        "オットランド",
        "フットビヤンコ",
        "ハグワール・D・サウロ",
        "ニコ・オルビア",
        "クマドリヤマンバ子",
        "スぺーシー中尉",
        "コスモ軍曹",
        "ギャラクシー将軍",
        "マクロ大佐",
        "霜月リューマ",
        "デュバル",
        "モトバロ",
        "ピーターマン",
        "シルバーズ・レイリー",
        "コーヒーモンキーズ",
        "スイトピー",
        "マーガレット",
        "アフェランドラ",
        "ベラドンナ",
        "キキョウ",
        "ネリネ",
        "ポピー",
        "パンジー",
        "エニシダ",
        "パンダウーマン美",
        "バキュラ",
        "ティバニー",
        "ヘラクレス",
        "パンクータ・ダケヤン",
        "ジャン・ゴエン",
        "アン・ゼンガイーナ",
        "ドビー・イバドンボ",
        "カイロ・クレヨ",
        "キノコ",
        "フランソワ",
        "ツノッコフ",
        "ウサッコフ",
        "ドーハ・イッタンカⅡ世",
        "チャドロス・ヒゲリゲス（茶ひげ）",
        "カーリー・ダダン",
        "ドグラ",
        "マグラ",
        "サンクリン",
        "アンモナイツ",
        "ジャン・ヌエイユ",
        "ロック",
        "スコッチ",
        "鉄筋のスムージ",
        "瓢箪 フェン・ボック",
        "縄引きのチャッペ",
        "錦えもん",
        "マチェーテのルン",
        "ガブル",
        "キュロス（片足の兵隊）",
        "スパルタン",
        "チンジャオ",
        "ケリー・ファンク",
        "ボビー・ファンク",
        "ジャン・アンゴ",
        "ウーシー",
        "マミー",
        "メドウズ",
        "アギョウ",
        "ダマスク",
        "ローリング・ローガン",
        "アキリア",
        "ランポー",
        "ペリーニ",
        "ヌーボン",
        "ボボンバ",
        "コットン",
        "ダイコン",
        "黒炭カン十郎",
        "マウジイ",
        "ウェリントン",
        "ロディ",
        "BB",
        "ワンダ",
        "キャロット",
        "ヨモ牧師",
        "ミヤギ",
        "トリスタン",
        "モンジイ",
        "シシリアン",
        "イヌアラシ",
        "ジョバンニ",
        "コンスロット",
        "ネコマムシ",
        "ペドロ",
        "ミルキー",
        "バリエテ",
        "雷ぞう",
        "ゼポ",
        "カルメル",
        "菊之丞（お菊）",
        "浦島",
        "アタゴ山",
        "傳ジロー（狂死郎）",
        "たぶ八郎",
        "地武えもん",
        "クロ沢",
        "カゲロウ",
        "しのぶ",
        "アシュラ童子（酒天丸）",
        "右近",
        "火太夫",
        "紋ジロウ",
        "十字ロウ",
        "カクの進",
        "コ十郎",
        "道たく",
        "スケさん",
        "クニさん",
        "カクさん",
        "ヒョウ五郎",
        "三ダユー",
        "雷刃",
        "スガミチ",
        "ワラザネ",
        "大黒",
        "風影",
        "風刃",
        "半ぞう",
        "ちょめ",
        "矢ざえもん",
        "地獄弁天",
        "猿飛",
        "ビシャ門",
        "福ロクジュ",
        "オニ丸（牛鬼丸）",
        "晴れ次",
        "ザン切丸",
        "河松",
        "雨月なみだ",
        "ホテイ",
        "飛室",
        "初芽",
        "がん吠",
        "がる弾",
        "大マサ",
        "綱ゴロー",
        "お蝶",
        "弥太っぺ",
        "霜月牛マル",
        "忍助",
        "霜月コウ三郎",
        "ぐる太郎",
        "勝ぞう",
        "ユルバンさん",
        "黒炭せみ丸",
        "黒炭ひぐらし",
        "ヤマト",
        "雨月天ぷら",
        "風月おむすび",
        "霜月フリコ",
        "ロロノア・ピンゾロ",
        "ロロノア・アラシ",
        "テラ",
        "すくね",
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

