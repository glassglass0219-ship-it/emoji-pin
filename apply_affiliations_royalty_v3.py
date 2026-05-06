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
        "バリウッド王国": ["ハン・バーガー"],
        "ビーフ王国": ["ストロガノフ"],
        "フラウス王国": ["バン・ドデシネ"],
        "プロデンス王国": ["ダガマ", "エリザベローⅡ世"],
        "ベストランド王国": ["レモンチーズ"],
        "ホワイトランド王国": ["イワトビ"],
        "南ファイアー王国": ["ジープ", "ホイール"],
        "モコモ公国": ["キャロット", "イヌアラシ", "ネコマムシ", "ひつギスカン公爵"],
        "リュウグウ王国": [
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
        ],
        "リンゴ王国": ["ナシ"],
        "ルブニール王国": ["アルユータヤン五世"],
        "ルルシア王国": ["コマネ", "セキ"],
        "ロシュワン王国": ["ビール６世", "マトリョーサカ", "マトリョースカ", "マトリョーセカ", "マトリョーソカ"],
        "ワノ国": ["光月モモの助", "光月スキヤキ（天狗山飛徹）", "光月日和（小紫）", "黒炭オロチ", "番三郎", "光月おでん", "光月トキ（天月トキ）"],
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
            if "王家" not in cats:
                cats.append("王家")
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

