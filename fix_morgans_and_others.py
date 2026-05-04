#!/usr/bin/env python3
"""ポログラム / サッチェルズ・マフィー / モーガンズ の改名、モルガンズ（id 602）への登場履歴マージ、重複キャラ削除。"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAR_PATH = ROOT / "src/data/characters.json"
MAP_PATH = ROOT / "src/data/manga_anime_map.json"

NAME_UPDATES: dict[str, str] = {
    "ポログラム": "ポーロ・グラム",
    "サッチェルズ・マフィー": "サッチェルズ・マッフィー宮",
    "モーガンズ": "モルガンズ",
}

RAW_MORGANS_EPS = [
    860,
    830,
    628,
    956,
    1090,
    825,
    865,
    1159,
    1096,
    1167,
    861,
    862,
    871,
    891,
    896,
    899,
    901,
    905,
    1086,
    872,
    903,
    864,
    1109,
    1113,
    1115,
    1117,
    1119,
    1124,
    1053,
    1074,
]

PRIMARY_MORGANS_ID = 602


def title_for_chapter(ep: int, manga_map: dict) -> str:
    entry = manga_map.get(str(ep))
    if isinstance(entry, dict):
        t = entry.get("title")
        if isinstance(t, str) and t.strip():
            return t.strip()
    return "最新話"


def patch_names_recursive(obj: object, old_to_new: dict[str, str]) -> None:
    if isinstance(obj, dict):
        n = obj.get("name")
        if isinstance(n, str) and n in old_to_new:
            obj["name"] = old_to_new[n]
        for v in obj.values():
            patch_names_recursive(v, old_to_new)
    elif isinstance(obj, list):
        for item in obj:
            patch_names_recursive(item, old_to_new)


def merge_appearances_primary_wins(
    primary: list[dict] | None, secondary: list[dict] | None, manga_map: dict
) -> list[dict]:
    """primary の話数・タイトルを優先し、secondary にのみある話を追加。"""
    by_ep: dict[int, str] = {}
    for a in primary or []:
        if not isinstance(a, dict) or "episode" not in a:
            continue
        ep = int(a["episode"])
        t = str(a.get("title", "")).strip()
        by_ep[ep] = t if t else title_for_chapter(ep, manga_map)
    for a in secondary or []:
        if not isinstance(a, dict) or "episode" not in a:
            continue
        ep = int(a["episode"])
        if ep in by_ep:
            continue
        t = str(a.get("title", "")).strip()
        by_ep[ep] = t if t else title_for_chapter(ep, manga_map)
    return [{"episode": ep, "title": by_ep[ep]} for ep in sorted(by_ep)]


def merge_morgans_with_ep_list(
    existing: list[dict] | None, new_eps: list[int], manga_map: dict
) -> list[dict]:
    """既存を保持しつつ new_eps の各話が無ければマップからタイトル付与で追加。"""
    by_ep: dict[int, str] = {}
    for a in existing or []:
        if not isinstance(a, dict) or "episode" not in a:
            continue
        ep = int(a["episode"])
        t = str(a.get("title", "")).strip()
        by_ep[ep] = t if t else title_for_chapter(ep, manga_map)
    for ep in new_eps:
        if ep not in by_ep:
            by_ep[ep] = title_for_chapter(ep, manga_map)
    return [{"episode": ep, "title": by_ep[ep]} for ep in sorted(by_ep)]


def run_fix() -> None:
    with CHAR_PATH.open(encoding="utf-8") as f:
        chars: list[dict] = json.load(f)
    with MAP_PATH.open(encoding="utf-8") as f:
        manga_map: dict = json.load(f)

    unique_sorted_eps = sorted(set(RAW_MORGANS_EPS))

    patch_names_recursive(chars, NAME_UPDATES)

    primary: dict | None = None
    for c in chars:
        if isinstance(c, dict) and int(c.get("id", -1)) == PRIMARY_MORGANS_ID:
            primary = c
            break

    if primary is None or primary.get("name") != "モルガンズ":
        print("⚠ id=602 のモルガンズが見つかりませんでした。")
    else:
        dupes: list[dict] = [
            c
            for c in chars
            if isinstance(c, dict)
            and c is not primary
            and c.get("name") == "モルガンズ"
        ]
        for d in dupes:
            primary["appearances"] = merge_appearances_primary_wins(
                primary.get("appearances"), d.get("appearances"), manga_map
            )
        chars[:] = [c for c in chars if c not in dupes]
        if dupes:
            print(f"✅ 重複モルガンズ {len(dupes)} 件を id {PRIMARY_MORGANS_ID} に統合して削除しました。")

        primary["appearances"] = merge_morgans_with_ep_list(
            primary.get("appearances"), unique_sorted_eps, manga_map
        )
        eps = [int(x["episode"]) for x in primary["appearances"]]
        if eps:
            primary["firstAppearance"] = min(eps)
        print(f"✅ モルガンズ（id {PRIMARY_MORGANS_ID}）の履歴を整理しました（全 {len(primary['appearances'])} 件）")

    for old, new in NAME_UPDATES.items():
        print(f"✅ '{old}' -> '{new}' に修正")

    chars.sort(key=lambda x: int(x.get("id", 0)))

    with CHAR_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)
        f.write("\n")


if __name__ == "__main__":
    run_fix()
