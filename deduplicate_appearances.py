#!/usr/bin/env python3
"""characters.json の appearances / covers から同一話数の重複を除去し、ソートする。"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAR_PATH = ROOT / "src" / "data" / "characters.json"


def _ep_key(ep: object) -> int | None:
    try:
        return int(ep)
    except (TypeError, ValueError):
        return None


def _title_score(title: object) -> int:
    """高いほど残したいタイトル。"""
    t = str(title or "").strip()
    if not t:
        return 0
    if "タイトル未設定" in t:
        return 1
    return 2


def _pick_better(a: dict, b: dict) -> dict:
    """同じ話数の 2 エントリのうち、タイトル品質が高い方を返す。"""
    sa = _title_score(a.get("title"))
    sb = _title_score(b.get("title"))
    if sa > sb:
        return a
    if sb > sa:
        return b
    la = len(str(a.get("title", "") or ""))
    lb = len(str(b.get("title", "") or ""))
    return a if la >= lb else b


def deduplicate() -> None:
    if not CHAR_PATH.exists():
        print("ファイルが見つかりません")
        return

    with CHAR_PATH.open(encoding="utf-8") as f:
        chars: list = json.load(f)

    total_removed = 0

    for char in chars:
        if not isinstance(char, dict):
            continue
        for key in ("appearances", "covers"):
            if key not in char or not isinstance(char[key], list):
                continue
            original_count = len(char[key])
            unique_entries: dict[int, dict] = {}
            no_episode: list[dict] = []

            for entry in char[key]:
                if not isinstance(entry, dict):
                    continue
                ek = _ep_key(entry.get("episode"))
                if ek is None:
                    no_episode.append(entry)
                    continue
                entry_norm = {**entry, "episode": ek}
                if ek in unique_entries:
                    unique_entries[ek] = _pick_better(unique_entries[ek], entry_norm)
                else:
                    unique_entries[ek] = entry_norm

            cleaned_list = [unique_entries[k] for k in sorted(unique_entries)]
            cleaned_list.extend(no_episode)
            char[key] = cleaned_list
            total_removed += original_count - len(cleaned_list)

    with CHAR_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"✅ 重複を削除しました。合計 {total_removed} 件の重複データを除去しました。")


if __name__ == "__main__":
    os.chdir(ROOT)
    deduplicate()
