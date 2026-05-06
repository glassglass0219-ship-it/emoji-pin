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
        "NEWスパイダーズカフェ": [
            "ジェム（Mr.5）",
            "ミキータ（ミス・バレンタイン）",
            "マリアンヌ（ミス・ゴールデンウィーク）",
            "ドロフィー（ミス・メリークリスマス）",
            "ベーブ（Mr.4）",
            "ザラ（ミス・ダブルフィンガー）",
            "ラッスー",
        ],
        "アマゾン・リリー": [
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
        ],
        "アラバスタ王国": ["コーザ", "おかめ", "ナットー", "ケビ", "ファラフラ", "エリック", "コアラ組"],
        "イエティクールブラザーズ": ["ロック", "スコッチ"],
        "エルバフ": ["ハグワール・D・サウロ"],
        "オハラ": ["ニコ・オルビア"],
        "オロチお庭番衆": ["雷刃", "スガミチ", "ワラザネ", "大黒", "風影", "風刃", "半ぞう", "ちょめ", "矢ざえもん", "地獄弁天", "猿飛", "ビシャ門", "福ロクジュ"],
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
            # choose smallest id if duplicates
            ch = min(bucket, key=lambda x: int(x.get("id", 10**9)))
            if ch.get("category") != "戦う者達":
                ch["category"] = "戦う者達"
                changed += 1
            g = ch.get("group")
            if not isinstance(g, list):
                g = [str(g).strip()] if str(g or "").strip() else []
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
    for n, ids in multi[:30]:
        print(f"MULTI {n} ids={ids}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

