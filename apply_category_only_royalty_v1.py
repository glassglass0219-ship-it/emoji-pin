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
    category_to_add = "王家"
    targets = [
        "ネフェルタリ・ビビ",
        "イガラム（Mr.8/イガラッポイ）",
        "カルー",
        "ワポル",
        "ドルトン",
        "チェス",
        "クロマーリモ",
        "タラッサ・ルーカス",
        "ネフェルタリ・コブラ",
        "マツゲ",
        "ペル",
        "チャカ",
        "ストンプ",
        "カウボーイ",
        "バーボンJr.",
        "ケンタロウス",
        "ヒコイチ",
        "金魚姫",
        "アロー",
        "ヒョウタ",
        "バレル",
        "ブラーム",
        "Dr.ホウ",
        "テラコッタ",
        "メイディ",
        "ネフェルタリ・ティティ",
        "キンデレラ",
        "アルユータヤン五世",
        "ウバウ",
        "グロリオーサ（ニョン婆）",
        "ボア・ハンコック",
        "ボア・サンダーソニア",
        "ボア・マリーゴールド",
        "エンポリオ・イワンコフ",
        "イゾウ",
        "ステリー",
        "フカボシ",
        "リュウボシ",
        "マンボシ",
        "ネプチューン",
        "ホエ",
        "メガロ",
        "右大臣",
        "左大臣",
        "しらほし",
        "オトヒメ",
        "錦えもん",
        "光月モモの助",
        "ヴィオラ（ヴァイオレット）",
        "ダガマ",
        "エリザベローⅡ世",
        "レベッカ",
        "タンク・レパント",
        "リク・ドルド3世（リッキー）",
        "ガンチョ",
        "スカーレット",
        "マンシェリー",
        "キャロット",
        "イヌアラシ",
        "ネコマムシ",
        "雷ぞう",
        "サリー・ナントカネット",
        "ヴィンスモーク・ヨンジ",
        "ヴィンスモーク・レイジュ",
        "ヴィンスモーク・ジャッジ",
        "ヴィンスモーク・イチジ",
        "ヴィンスモーク・ニジ",
        "コゼット",
        "エポニー",
        "ヴィンスモーク・ソラ",
        "猫車",
        "セーザ",
        "イワトビ",
        "ラーメン",
        "コマネ",
        "ビール６世",
        "マトリョーサカ",
        "マトリョースカ",
        "マトリョーセカ",
        "マトリョーソカ",
        "ハン・バーガー",
        "モロロン",
        "タコス",
        "ムケッカ",
        "ナシ",
        "マリ",
        "ソース",
        "ネギー",
        "クーラン",
        "レモンチーズ",
        "ジープ",
        "ホイール",
        "フラーリ",
        "トリトブー",
        "セキ",
        "ストロガノフ",
        "ティー４世",
        "バン・ドデシネ",
        "チャップ",
        "光月スキヤキ（天狗山飛徹）",
        "菊之丞（お菊）",
        "傳ジロー（狂死郎）",
        "しのぶ",
        "アシュラ童子（酒天丸）",
        "光月日和（小紫）",
        "黒炭オロチ",
        "河松",
        "ヴァンサン",
        "番三郎",
        "光月おでん",
        "光月トキ（天月トキ）",
        "ひつギスカン公爵",
        "ネフェルタリ・リリィ",
        "べコリ",
        "ブルドッグ",
        "コニー",
        "トリトマ",
        "ロキ",
        "ハラルド",
        "エストリッダ",
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

