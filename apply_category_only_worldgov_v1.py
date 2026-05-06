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
    category_to_add = "世界政府"
    targets = [
        "カク",
        "カリファ",
        "ロブ・ルッチ",
        "ハットリ",
        "コーギー",
        "ブルーノ",
        "ジョルジ裁判長",
        "スパンダム",
        "ジェリー",
        "ワンゼ",
        "ネロ",
        "ジャブラ",
        "フクロウ",
        "クマドリ",
        "ギャサリン",
        "バスカビル",
        "法の番犬部隊",
        "有罪陪審員",
        "スパンダイン",
        "ラスキー",
        "ツムッシュ・カマヤ",
        "ファンクフリード",
        "パシフィスタ",
        "ハンニャバル",
        "ドミノ",
        "ブルーゴリラ（ブルゴリ）",
        "マゼラン",
        "バシリスク",
        "パズルサソリ",
        "サルデス",
        "マンティコラ",
        "サディちゃん",
        "スフィンクス",
        "ミノタウロス",
        "ミノリノケロス",
        "ミノコアラ",
        "ミノゼブラ",
        "ムチャナー",
        "軍隊ウルフ",
        "スコシバ・カニシトール",
        "伝書バット",
        "コング",
        "ミノチワワ",
        "ジスモンダ",
        "ヨセフ",
        "ゲルニカ",
        "ステューシー",
        "ジャバリ",
        "フーズ・フー",
        "S-スネーク",
        "S-ホーク",
        "S-ベア",
        "パシフィスタ POLICE",
        "S-シャーク",
        "パシフィスタ マークⅢ",
        "セラフィム（ドンキホーテ・ドフラミンゴ）",
        "セラフィム（ゲッコー・モリア）",
        "セラフィム（クロコダイル）",
        "アルファ",
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

