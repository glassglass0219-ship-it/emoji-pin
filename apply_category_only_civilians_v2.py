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
    category_to_add = "市民"
    targets = [
        "メロ",
        "セイラ",
        "イチカ",
        "ニカ",
        "サンカ",
        "ヨンカ",
        "ヨンカツー",
        "ジュナン",
        "マキノの子供",
        "サーファンクル",
        "パパニール",
        "ズルーリン",
        "ムティ",
        "ナンデー",
        "マリア・ナポレ",
        "ブレイキー",
        "マイルス",
        "トンジル",
        "トンスファー",
        "アリーチェ",
        "ビミネ",
        "シンド",
        "モチャ",
        "コンブ",
        "ビヨ",
        "アリー",
        "ドラン",
        "ウズ",
        "バブル",
        "マリオ",
        "ギャッツ",
        "アレモ・ガンミー",
        "ムッカシミ・タワー",
        "エスタ",
        "ミロ（ワンポコ）",
        "グラバー",
        "トラファルガー・ラミ",
        "ルシアン",
        "ギムレット",
        "シン・ジャイヤ",
        "シン・デタマルカ",
        "テガタ・リンガナ",
        "パウンド",
        "ル・フェルド",
        "モルガンズ",
        "ドラッグ・ピエクロ",
        "ギバーソン",
        "ウミット",
        "ジグラ",
        "ヴィクトリア・シルトン・ドルヤナイカ",
        "オイデー",
        "港友",
        "津軽うみ",
        "義浪チン太郎",
        "遠山辻ギロー",
        "お玉（黒炭 玉）",
        "お鶴",
        "セリザワ",
        "わかさ",
        "ひろし",
        "一鶴",
        "ようかん",
        "キン坊",
        "お八女",
        "いの一番の助",
        "銀のすけ",
        "千早",
        "お蝶々",
        "ごろ兵衛",
        "カメ吉",
        "割野フリ四郎",
        "悪代カン三郎",
        "トコ",
        "お高（高尾）",
        "びん豪",
        "ブン業",
        "凡ゴウ",
        "半次",
        "クマ五郎",
        "幸ベエ",
        "きせ川",
        "時ジロー",
        "らくだ",
        "霜月康イエ（トの康）",
        "小糸",
        "麻七",
        "犬飼",
        "鶴江もんの助",
        "あずき",
        "玄林",
        "のり子",
        "保井さっ左",
        "地獄釜蓋 目我点藩血ロウ",
        "山車天矢朗",
        "引込突米",
        "多美化羽織",
        "合点承知の助男",
        "寿限無寿限無子",
        "長久命の長助",
        "霜月コウ三郎",
        "トマティート",
        "でい五郎",
        "フリカ",
        "エッタラ・チャウンカイ",
        "大岩",
        "小岩",
        "中岩",
        "友ぞう",
        "マウストゥー・マウスヤン",
        "ノリの助",
        "レノナ・トパッカ",
        "デモーニ・アイヨ",
        "安馬",
        "お貴",
        "うっかりツル兵衛",
        "お染",
        "福み",
        "千利休留",
        "ジョシュ",
        "イヤンエーノウ・チノデ",
        "コロン",
        "マト",
        "クラップ",
        "ニョルニョ・ニャルマーニ",
        "アンジェ",
        "イルヴァ",
        "ローニャ",
        "マグ",
        "エーギル",
        "リプリー",
        "ベガパンツ",
        "スカルディ",
        "ヨハンナ",
        "ブレイド",
        "キバ",
        "ウォルフ",
        "オラブ",
        "カリン",
        "ビョルン",
        "ベント",
        "イーダ",
        "マグノリア",
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

