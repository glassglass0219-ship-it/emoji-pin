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
        "ルルシア王国": ["モーダ", "キュージ", "コーダ"],
        "ローグタウン": ["アンジョウ", "ハンガーさん", "いっぽんマツ", "いっぽんウメ", "サピー", "ユウ"],
        "ロングリングロングランド": ["シェリー", "トンジット", "トンジル", "トンスファー"],
        "ワノ国": [
            "港友",
            "津軽うみ",
            "義浪チン太郎",
            "遠山辻ギロー",
            "お玉（黒炭 玉）",
            "お鶴",
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
            "でい五郎",
            "大岩",
            "小岩",
            "中岩",
            "友ぞう",
            "ノリの助",
            "安馬",
            "お貴",
            "うっかりツル兵衛",
            "お染",
            "福み",
            "千利休留",
        ],
        "温泉島": ["ゴロー"],
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

