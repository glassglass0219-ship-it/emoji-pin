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
        "アンジョウ",
        "マキノ",
        "ギョルさん",
        "チキンおばさん",
        "ウープ・スラップ",
        "リカ",
        "リリカ",
        "くいな",
        "コウシロウ",
        "シュシュ",
        "ブードル",
        "ホッカー",
        "ポロ",
        "モーニン",
        "にんじん",
        "ピーマン",
        "たまねぎ",
        "カヤ",
        "門番",
        "メリー",
        "バンキーナ",
        "モッツェルおじさん",
        "ムーディ",
        "ロクサーヌ",
        "みなともさん",
        "ナミ魚人",
        "チャボ",
        "ノジコ",
        "ゲンゾウ",
        "Dr.ナコー",
        "ダディーディー",
        "マミーミー",
        "サム",
        "ハンガーさん",
        "いっぽんマツ",
        "いっぽんウメ",
        "サピー",
        "ユウ",
        "サムライ・バッツ",
        "ユキ",
        "ネギ熊まりあ",
        "タマチビ",
        "くれは",
        "イッシー100（イッシー20）",
        "ヒルルク",
        "ヨシモトさん",
        "トト",
        "コーザ",
        "おかめ",
        "ナットー",
        "ケビ",
        "アスワ",
        "カッパ",
        "ファラフラ",
        "エリック",
        "ウルトラキング",
        "オクトパ子",
        "ハチマキナマズ村の長老",
        "Dr.ポツーン",
        "スペクトルさん",
        "テリー",
        "親方",
        "アマゾン",
        "コニス",
        "スー",
        "パガヤ",
        "アイサ",
        "ラキ",
        "イーサ",
        "賢者ゴーデ",
        "モイル",
        "モチ",
        "Dr.クロツル",
        "モーダ",
        "ムース",
        "ハーブ",
        "マリリン",
        "キュージ",
        "コーダ",
        "シェリー",
        "トンジット",
        "ゴロー",
        "チムニー",
        "ゴンベ",
        "ココロ",
        "ミショイン・キャシブル",
        "ザンバイ",
        "ショルゾウ",
        "コップ",
        "タマゴン",
        "キエフ",
        "イーシゴ・シテマンナ",
        "アイスバーグ",
        "ティラノサウルス",
        "パウリー",
        "ピープリー・ルル",
        "カクカクさん",
        "Dr.キューキュー",
        "キウイ",
        "モズ",
        "タイルストン",
        "ハッパ・ヤマオ",
        "トム",
        "ブション",
        "ステイビー",
        "ソドム",
        "ゴモラ",
        "マイケル",
        "ホイケル",
        "ロジ",
        "ミズイラ",
        "オラン",
        "ブッシリ",
        "ロシュ",
        "ハック（オハラの学者）",
        "リント",
        "グラム",
        "ゼイディー",
        "ホチャ",
        "クラウ・D・クローバー",
        "カネゼニー",
        "ニゲラッタ",
        "アタッチ",
        "マルミエータ",
        "ヤメナハーレ",
        "ツキミ博士",
        "スポイルじいさん",
        "エーガナ",
        "マルガリータ",
        "ケイミー",
        "パッパグ",
        "アントニオ",
        "シャクヤク（シャッキー）",
        "マリィ",
        "ジュディ",
        "マリン",
        "ディスコ",
        "パシア",
        "ハレダス",
        "タロイモ",
        "シャンバ",
        "ロイダー",
        "ポートガス・D・ルージュ",
        "アウトルック3世",
        "ディディット",
        "アッホ・デスネン9世",
        "アッホ・ヅラコ",
        "カサ婆",
        "ハンフリー",
        "ビーク・リマーク",
        "イシリー",
        "ルリス",
        "ソラ",
        "シャーリー",
        "フィヨンセ",
        "ヒラメラ",
        "カイレン",
        "デン",
        "アデル",
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

