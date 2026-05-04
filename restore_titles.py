#!/usr/bin/env python3
"""characters.json の登場情報から 1〜1114 話のタイトルを manga_anime_map.json に復元する（1115 以降は変更しない）。"""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAR_PATH = ROOT / "src/data/characters.json"
MAP_PATH = ROOT / "src/data/manga_anime_map.json"


def rescue_titles() -> None:
    with CHAR_PATH.open(encoding="utf-8") as f:
        chars = json.load(f)

    captured_titles: dict[int, str] = {}
    for c in chars:
        for app in c.get("appearances") or []:
            if not isinstance(app, dict):
                continue
            try:
                ep = int(app.get("episode"))
            except (TypeError, ValueError):
                continue
            title = (app.get("title") or "").strip()
            if ep > 1114 or not title or "タイトル未設定" in title:
                continue
            if ep not in captured_titles or len(title) > len(captured_titles[ep]):
                captured_titles[ep] = title

    with MAP_PATH.open(encoding="utf-8") as f:
        manga_map = json.load(f)

    restore_count = 0
    for ep_num in range(1, 1115):
        s_ep = str(ep_num)
        if s_ep in manga_map:
            entry = manga_map[s_ep]
            if not isinstance(entry, dict):
                entry = {"ep": entry} if entry is not None else {}
                manga_map[s_ep] = entry
            current_title = (entry.get("title") or "").strip()
            if (not current_title or "タイトル" in current_title) and ep_num in captured_titles:
                entry["title"] = captured_titles[ep_num]
                restore_count += 1
        elif ep_num in captured_titles:
            manga_map[s_ep] = {"title": captured_titles[ep_num]}
            restore_count += 1

    with MAP_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(manga_map, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"[OK] {restore_count} 件のエピソードタイトルを復元しました。")


if __name__ == "__main__":
    rescue_titles()
