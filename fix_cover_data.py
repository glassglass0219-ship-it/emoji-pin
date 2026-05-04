#!/usr/bin/env python3
"""appearances から指定話を削除し covers（扉絵一覧）へ移す。"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAR_PATH = ROOT / "src/data/characters.json"

move_list: dict[str, list[int]] = {
    "ヤマト": [1116, 1117, 1118, 1119, 1120, 1121, 1123, 1124, 1125, 1126, 1127, 1129, 1130, 1131, 1132, 1133],
    "光月日和": [1115],
    "トコ": [1115],
    "お鶴": [1116],
    "浦島": [1116],
    "ネコマムシ": [1117],
    "ヒョウ五郎": [1117],
    "傳ジロー": [1120, 1123],
    "しのぶ": [1129],
    "お玉": [1129, 1130, 1131, 1132, 1133, 1135, 1136],
    "小紫": [1129, 1131, 1132, 1136],
    "スピード": [1131, 1132, 1133, 1136],
    "ホールデム": [1133, 1135, 1136],
    "錦えもん": [1133, 1135, 1136],
    "フーズ・フー": [1138, 1139],
    "ページワン": [1139],
    "うるティ": [1139],
}

# move_list のキーに対し、JSON 上の name / alias と突き合わせる別名（表記揺れ）
NAME_VARIANTS: dict[str, list[str]] = {
    "光月日和": ["光月日和", "小紫", "光月ヒヨリ"],
    "お鶴": ["お鶴", "鶴条"],
    "傳ジロー": ["傳ジロー", "電次郎"],
    "ヒョウ五郎": ["ヒョウ五郎", "兵五郎"],
}


def norm_key(s: str) -> str:
    t = re.sub(r"[・\s\-_]", "", (s or "").strip())
    while len(t) > 1 and t.endswith("聖"):
        t = t[:-1]
    return t


def char_name_norm_keys(c: dict) -> set[str]:
    keys: set[str] = set()
    nm = c.get("name") or ""
    keys.add(norm_key(nm))
    if nm.startswith("光月") and len(nm) > 2:
        keys.add(norm_key(nm[2:]))
    al = str(c.get("alias") or "")
    for part in re.split(r"[,、／/]", al):
        p = part.strip()
        if p:
            keys.add(norm_key(p))
    return keys


def character_matches_rule(c: dict, rule_key: str) -> bool:
    variants = NAME_VARIANTS.get(rule_key, [rule_key])
    cn = char_name_norm_keys(c)
    return any(norm_key(v) in cn for v in variants)


def ensure_cover_title(title: str) -> str:
    t = str(title or "").strip()
    if t.endswith("の扉絵"):
        return t
    if not t:
        return "の扉絵"
    # 1 文字タイトル（例: 1117「も」）にそのまま「の扉絵」を付けると「もの扉絵」と誤読される
    if len(t) == 1:
        return f"「{t}」の扉絵"
    return t + "の扉絵"


def _ep_key(x: dict) -> int:
    try:
        return int(x.get("episode"))
    except (TypeError, ValueError):
        return 0


def run_fix() -> None:
    with CHAR_PATH.open(encoding="utf-8") as f:
        chars: list[dict] = json.load(f)

    total_moved = 0

    for char in chars:
        if not isinstance(char, dict):
            continue

        target_eps: set[int] = set()
        for rule_key, eps in move_list.items():
            if character_matches_rule(char, rule_key):
                target_eps.update(int(e) for e in eps)

        if not target_eps:
            continue

        apps = char.get("appearances")
        if not isinstance(apps, list):
            continue

        covers = char.setdefault("covers", [])
        if not isinstance(covers, list):
            char["covers"] = []
            covers = char["covers"]

        existing_cover_eps = {
            int(c.get("episode"))
            for c in covers
            if isinstance(c, dict) and c.get("episode") is not None
        }

        to_move = []
        kept: list[dict] = []
        for a in apps:
            if not isinstance(a, dict):
                kept.append(a)
                continue
            try:
                ep = int(a.get("episode"))
            except (TypeError, ValueError):
                kept.append(a)
                continue
            if ep in target_eps:
                to_move.append(dict(a))
            else:
                kept.append(a)

        for entry in to_move:
            entry["title"] = ensure_cover_title(str(entry.get("title", "")))
            ep = int(entry["episode"])
            if ep not in existing_cover_eps:
                covers.append(entry)
                existing_cover_eps.add(ep)
                total_moved += 1

        char["appearances"] = kept
        kept.sort(key=_ep_key)
        covers.sort(key=_ep_key)

    chars.sort(key=lambda x: int(x["id"]) if isinstance(x, dict) and "id" in x else 0)

    with CHAR_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"✅ 合計 {total_moved} 件の登場データを扉絵一覧へ移動しました。")


if __name__ == "__main__":
    run_fix()
