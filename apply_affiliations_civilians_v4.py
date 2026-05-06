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
        "ナガグツ王国": ["ニョルニョ・ニャルマーニ"],
        "ハチマキナマズ村": ["ハチマキナマズ村の長老"],
        "バテリラ": ["ポートガス・D・ルージュ"],
        "バルジモア": ["タロイモ"],
        "パンクハザード": ["シンド", "モチャ", "コンブ", "ビヨ", "アリー", "ドラン", "ウズ"],
        "パンプキンカフェ": ["コニス", "ラキ"],
        "フーシャ村": ["マキノ", "ギョルさん", "チキンおばさん", "ウープ・スラップ", "みなともさん", "マキノの子供"],
        "元アラバスタ反乱軍": ["ファラフラ", "エリック"],
        "元ウソップ海賊団": ["にんじん", "ピーマン", "たまねぎ"],
        "元ドラム王国": ["ヒルルク"],
        "リュウグウ王国": [
            "ナミ魚人",
            "オクトパ子",
            "ケイミー",
            "パッパグ",
            "イシリー",
            "ルリス",
            "ソラ",
            "シャーリー",
            "フィヨンセ",
            "ヒラメラ",
            "カイレン",
            "デン",
            "アデル",
            "メロ",
            "セイラ",
            "イチカ",
            "ニカ",
            "サンカ",
            "ヨンカ",
            "ヨンカツー",
            "ジュナン",
            "パパニール",
            "ズルーリン",
            "マリア・ナポレ",
            "ブレイキー",
            "マイルス",
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

            if ch.get("category") != "市民":
                ch["category"] = "市民"
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

