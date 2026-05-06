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

    assignments: dict[str, list[str]] = {
        "リトル海賊団": ["リトルオーズJr."],
        "ルンバー海賊団": ["ラブーン", "ヨーキ", "ミズータ・マダイスキー", "ミズータ・マワリトスキー"],
        "ローリング海賊団": ["シャーロット・ローラ", "リスキー兄弟"],
        "ロシオ海賊団": ["ロシオ"],
        "猿山連合軍": ["モンブラン・クリケット"],
        "巨兵海賊団": ["ブロギー", "ドリー", "カーシー", "オイモ", "トールマン"],
        "金獅子海賊団": ["シキ（金獅子）", "Dr.インディゴ"],
        "九蛇海賊団": [
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
            "トリトマ",
        ],
        "元ベラミー海賊団": ["ベラミー", "サーキース", "リリー", "リヴァーズ", "ロス", "エディ", "ヒューイット", "マニ", "ミュレ"],
        "元巨兵海賊団": ["ライディーン", "ヨルル", "ヤルル"],
        "黒ひげ海賊団": [
            "ラフィット",
            "ジーザス・バージェス",
            "ヴァン・オーガー",
            "マーシャル・D・ティーチ（黒ひげ）",
            "ドクQ",
            "ストロンガー",
            "クザン（青雉）",
            "シリュウ",
            "サンファン・ウルフ",
            "バスコ・ショット",
            "カタリーナ・デボン",
            "アバロ・ピサロ",
            "キキパツ",
            "マキ",
            "トリ",
        ],
        "新巨兵海賊団": ["スタンセン", "ハイルディン", "ゲルズ", "ロード", "ゴールドバーグ"],
        "新魚人海賊団": ["ハモンド", "カサゴバ", "ヒョウゾウ", "ホーディ・ジョーンズ", "ドスン", "ゼオ", "ダルマ", "イカロス・ムッヒ"],
        "大カブト海賊団": ["ミカヅキ"],
        "大渦蜘蛛海賊団": ["スクアード"],
        "茶ひげ海賊団": ["チャドロス・ヒゲリゲス（茶ひげ）"],
        "桃ひげ海賊団": ["桃ひげ"],
        "破戒僧海賊団": ["ウルージ"],
        "白ひげ海賊団": [
            "ポートガス・D・エース",
            "エドワード・ニューゲート（白ひげ）",
            "テート",
            "マルコ",
            "ジョズ",
            "サッチ",
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
            "キングデュー",
        ],
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

            cats = ensure_list(ch.get("category"))
            if "海賊" not in cats:
                cats.append("海賊")
                ch["category"] = cats
                changed += 1

            groups = ensure_list(ch.get("group"))
            if group not in groups:
                groups.append(group)
                ch["group"] = groups
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

