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
    for ch in ["・", "･", "“", "”", "〝", "〟", "「", "」", "『", "』"]:
        t = t.replace(ch, "")
    return t


def ensure_group_list(c: dict) -> list[str]:
    g = c.get("group")
    if isinstance(g, list):
        out: list[str] = []
        seen: set[str] = set()
        for x in g:
            if not isinstance(x, str):
                continue
            t = x.strip()
            if not t or t in seen:
                continue
            seen.add(t)
            out.append(t)
        return out
    if isinstance(g, str):
        t = g.strip()
        return [t] if t else []
    return []


def main() -> int:
    path = Path("src/data/characters.json")
    chars = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(chars, list):
        raise SystemExit("characters.json must be a list")

    idx: dict[str, list[dict]] = {}
    for c in chars:
        if not isinstance(c, dict):
            continue
        nm = str(c.get("name") or "")
        if not nm:
            continue
        idx.setdefault(norm_name(nm), []).append(c)

    # category=戦う者達
    assignments: dict[str, list[str]] = {
        "ボーイン列島": ["ヘラクレス"],
        "見廻組": ["ホテイ", "飛室", "初芽", "がん吠", "がる弾", "ぐる太郎"],
        "モガロ王国": ["ケリー・ファンク", "ボビー・ファンク"],
        "モコモ公国": [
            "ロディ",
            "BB",
            "ワンダ",
            "キャロット",
            "ヨモ牧師",
            "ミヤギ",
            "トリスタン",
            "モンジイ",
            "シシリアン",
            "ジョバンニ",
            "コンスロット",
            "ペドロ",
            "ミルキー",
            "バリエテ",
        ],
        "元アーロン一味": ["はっちゃん"],
        "ヨサクとジョニー": ["ヨサク", "ジョニー"],
        "リュウグウ王国": ["アンモナイツ", "ジャン・ヌエイユ"],
        "ルブニール王国探検船": ["モンブラン・ノーランド", "Dr.ホンナー"],
        "ワノ国": [
            "霜月リューマ",
            "浦島",
            "アタゴ山",
            "たぶ八郎",
            "地武えもん",
            "クロ沢",
            "カゲロウ",
            "しのぶ",
            "右近",
            "火太夫",
            "紋ジロウ",
            "十字ロウ",
            "カクの進",
            "コ十郎",
            "道たく",
            "三ダユー",
            "オニ丸（牛鬼丸）",
            "晴れ次",
            "ザン切丸",
            "雨月なみだ",
            "大マサ",
            "綱ゴロー",
            "お蝶",
            "弥太っぺ",
            "霜月牛マル",
            "忍助",
            "霜月コウ三郎",
            "勝ぞう",
            "黒炭せみ丸",
            "黒炭ひぐらし",
            "雨月天ぷら",
            "風月おむすび",
            "すくね",
        ],
        "ワノ国 赤鞘九人男": [
            "錦えもん",
            "黒炭カン十郎",
            "イヌアラシ",
            "ネコマムシ",
            "雷ぞう",
            "菊之丞（お菊）",
            "傳ジロー（狂死郎）",
            "アシュラ童子（酒天丸）",
            "河松",
        ],
        "海上レストランバラティエ": ["ゼフ", "パティ", "カルネ"],
        "狂死郎一家": ["スケさん", "クニさん", "カクさん"],
        "元B・W（バロックワークス）": [
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
            "F-ワニ",
            "ラッスー",
            "Mr.7（元）",
            "ミス・ファーザーズデー",
            "Mr.7",
            "Mr.ラブ",
        ],
        "元海軍第153支部": ["モーガン"],
        "元海軍本部": ["クザン（青雉）"],
        "元八宝水軍": ["チンジャオ"],
        "神の守護者": ["マッキンリー"],
        "人生バラ色ライダーズ": ["デュバル", "モトバロ"],
        "珍獣島": ["ガイモン"],
        "マジアツカ王国": ["ローリング・ローガン"],
    }

    changed = 0
    missing: list[str] = []
    multi: list[tuple[str, list[int]]] = []

    for group, names in assignments.items():
        for name in names:
            bucket = idx.get(norm_name(name)) or []
            if not bucket:
                missing.append(name)
                continue
            if len(bucket) > 1:
                ids = sorted(int(x.get("id", 10**9)) for x in bucket)
                multi.append((name, ids))
            ch = min(bucket, key=lambda x: int(x.get("id", 10**9)))

            if ch.get("category") != "戦う者達":
                ch["category"] = "戦う者達"
                changed += 1

            g = ensure_group_list(ch)
            if group not in g:
                g.append(group)
                ch["group"] = g
                changed += 1

    chars.sort(key=lambda x: int(x.get("id", 0)) if isinstance(x, dict) else 0)
    path.write_text(json.dumps(chars, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    print(f"changed={changed}")
    print(f"missing_count={len(missing)}")
    for m in missing:
        print(f"MISSING {m}")
    print(f"multi_hit_count={len(multi)}")
    for n, ids in multi[:50]:
        print(f"MULTI {n} ids={ids}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

