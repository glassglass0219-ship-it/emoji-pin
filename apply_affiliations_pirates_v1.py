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

    assignments: dict[str, list[str]] = {
        "アーロン一味": ["アーロン", "カネシロ", "ピサロ", "チュウ", "クロオビ", "シオヤキ", "タケ"],
        "赤髪海賊団": [
            "モンスター",
            "シャンクス",
            "ラッキー・ルウ",
            "ヤソップ",
            "ベン・ベックマン",
            "ロックスター",
            "ボンク・パンチ",
            "ライムジュース",
            "ホンゴウ",
            "〝ハウリング〟ガブ",
            "ビルディング・スネイク",
        ],
        "赤髪傘下の海賊": ["オリ婆", "玉指ゲロティニー", "慰霊刃のフガー", "ブルブルのプルル", "着火のリナリア"],
        "アクメイト海賊団": ["デビル・ディアス"],
        "アルビダ海賊団": ["ヘッポコ", "ペッポコ", "ポッポコ"],
        "イエス海賊団": ["パッキー", "コゼ"],
        "イデオ海賊団": ["アブドーラ", "ジェット", "イデオ", "ブルーギリー"],
        "オンエア海賊団": ["スクラッチメン・アプー"],
        "カリブー海賊団": ["モーム", "カリブー", "コリブー"],
        "キッド海賊団": [
            "ユースタス・キッド",
            "キラー（鎌ぞう）",
            "ヒート",
            "ワイヤー",
            "UK",
            "ポンプ",
            "バブルガム",
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

            if ch.get("category") != "海賊":
                ch["category"] = "海賊"
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

