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
        "アギー68",
        "バットマン",
        "ガゼルマン",
        "マウスマン",
        "ホールデム",
        "ラビットマン",
        "スピード",
        "噛二郎",
        "さらへび先生",
        "プドス",
        "キキパツ",
        "マキ",
        "トリ",
        "アルベル（キング）",
        "サイエン（クイーン）",
        "イビリブツ",
        "ドウナンノヨ",
        "ドボン",
        "ページワン",
        "アルパカマン",
        "ソリティア",
        "ダイフゴー",
        "ババヌキ",
        "ノコッティ",
        "ウワッツラー",
        "マジロマン",
        "ノドイ・ワカーン",
        "ヒッパン・ナッテ",
        "ネオキ",
        "ウラヤ・マシカッタ",
        "シーガル・ガンズ・ノズドン",
        "サンベル",
        "ホークマン",
        "KOSHIファルコン",
        "AGEHAウーマン",
        "スーカレ・タイネン",
        "シコン・ケッタイ",
        "メザスゾワン・ピースオ",
        "ラクシテモ・テルスベハナイカ博士",
        "スーカレ・カレホスイ",
        "サライ",
        "スコッパー・ギャバン",
        "ミレ・パイン",
        "眼竜",
        "ドリンゴ",
        "タロウ",
        "ピータームー",
        "ドンキーノ",
        "CBギャラン",
        "ユーイ",
        "ムーン・アイザックJr.",
        "スペンサー",
        "Mr.モモラ",
        "ローウィング",
        "エリオ",
        "バンクロ",
        "ジャクソンバナー",
        "うるティ",
        "フーズ・フー",
        "ブラックマリア",
        "ササキ",
        "バオファン",
        "ジャンパー",
        "ビーガール",
        "バッタマン",
        "提灯マン",
        "うすのろ",
        "ナイトクラブガール",
        "ダウト兄弟",
        "レッドウルフ",
        "八茶",
        "ノコクワポリス",
        "ビートルマン",
        "カマキリガール",
        "ハクガン",
        "七鬼",
        "四鬼",
        "五鬼",
        "十鬼",
        "ブリスコラ",
        "サイタンク",
        "スコーピオンレディ",
        "ビズリー",
        "コーカサスマン",
        "ハムレット",
        "フォートリックス",
        "ミゼルカ",
        "ゴリ四郎",
        "ポーカー",
        "びしょ濡れ女",
        "山姥",
        "濡れ女",
        "天井下り",
        "コタツ",
        "コーネリア",
        "ウブロ",
        "ガンリュウ",
        "レオネロ",
        "スカル",
        "マハ",
        "カイマンレディ",
        "ヘラ",
        "ホースマン",
        "輪入道",
        "九忍",
        "UK",
        "ポンプ",
        "バブルガム",
        "一美",
        "二牙",
        "三鬼",
        "レック",
        "ハウス",
        "ブギ",
        "モッシュ",
        "ヒップ",
        "パパス",
        "ジャガー",
        "クインシー",
        "モアイ",
        "ギグ",
        "ダイブ",
        "エマ",
        "ホップ",
        "コンポ",
        "ディスクJ",
        "六鬼",
        "ボンク・パンチ",
        "ライムジュース",
        "ホンゴウ",
        "〝ハウリング〟ガブ",
        "ビルディング・スネイク",
        "オリ婆",
        "玉指ゲロティニー",
        "慰霊刃のフガー",
        "ブルブルのプルル",
        "着火のリナリア",
        "ガンズイ",
        "ギル・バスター",
        "シキ（金獅子）",
        "パート",
        "ポテト",
        "ギョギョ",
        "トッツ",
        "トリトマ",
        "ハナフダ",
        "シミター太",
        "ヒッピー・ザ・ドクロカレー",
        "ヒロ★ゴーモン",
        "ジョイボーイ",
        "トールマン",
        "ロックス・D・ジーベック（デービー・D・ジーベック）",
        "首領・マーロン",
        "王直",
        "ミュグレン大佐",
        "ラングラム",
        "凶（銀斧）",
        "バーベル",
        "エリス",
        "ブルマリン",
        "ヤモン",
        "ポーロ・グラム",
        "Dr.インディゴ",
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

