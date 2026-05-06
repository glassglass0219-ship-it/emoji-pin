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
        "クライガナ島": ["ヒューマンドリル"],
        "サクラ王国": ["ハイキングベア", "ラパーン"],
        "シェルズタウン": ["ソーロ"],
        "ジャヤ": ["サウスバード", "カシ神", "カシ神の子", "ノースバード", "ウエスタンバード", "イースタンバード"],
        "シャンディア": ["ノラ"],
        "スカイピア": ["タコバルーン"],
        "スフィンクス": ["タマ"],
        "トリノ王国": ["マスケレドモ・ゴアユー鳥"],
        "ドレスローザ王国": ["闘魚"],
        "トンタッタ王国": ["イエローカブ（山吹オオカブトムシ）", "ピンクビー（桃色スズメバチ）", "リニアフォックス"],
        "パンクハザード": ["ドラゴン十三號", "スマイリー", "ドラゴン二十一號"],
        "フーシャ村": ["近海の主（ゴア王国）"],
        "モコモ公国": ["ワーニー"],
        "元ドラム王国": ["ロブソン", "スノウバード（雪鳥）"],
        "リトルガーデン": ["ブロントザウルス", "島食い"],
        "リュウグウ王国": ["海獅子", "海リス", "海熊"],
        "ロングリングロングランド": ["ダッ～～～～クスフント", "カ～～～～モノハシ", "ユキヒョ～～～～ウ", "近海の主（ロングリングロングランド）"],
        "ワノ国": [
            "ガマ・ピョンの助",
            "春ダコ",
            "夢鯉",
            "ひひ丸",
            "マッドサウルス",
            "狛ちよ",
            "ぶんぶく君",
            "ワニザメ",
            "狛鹿",
            "さいころ",
            "タニシ",
            "ホメ",
            "三助",
            "狛デーン",
            "狛鶏",
            "狛虎",
            "小山",
            "山さん",
            "忠治",
        ],
        "悪ブラックドラム王国": ["ハコワン"],
        "温泉島": ["土番長", "森番長"],
        "元新魚人海賊団": ["スルメ"],
        "珍獣島": ["ココックス"],
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
            if "その他" not in cats:
                cats.append("その他")
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

