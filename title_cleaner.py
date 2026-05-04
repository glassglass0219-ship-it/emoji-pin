"""
manga_anime_map.json / characters.json 内のタイトルから Wiki 記法を除去する。

{{Ruby|漢字|ルビ}} は第1表示引数へ、その他 {{...}} は除去。
ネスト・未閉じテンプレは fandom_updater.strip_wiki_markup_to_plain_title と同じ規則で処理。
"""

from __future__ import annotations

import json
import os
import re
import sys

from fandom_updater import strip_wiki_markup_to_plain_title

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.abspath(__file__))
MAP_PATH = os.path.join(ROOT, "src", "data", "manga_anime_map.json")
CHAR_PATH = os.path.join(ROOT, "src", "data", "characters.json")


def clean_title(title: str | None) -> str:
    if title is None or title == "":
        return ""
    t = strip_wiki_markup_to_plain_title(str(title))
    # 壊れたテンプレ断片（{{Ruby のみ等）で残りがちなノイズ
    t = re.sub(r"\s*Web ref\s*$", "", t, flags=re.I).strip()
    t = re.sub(r"\s+", " ", t).strip()
    if t.casefold() == "ruby":
        return "タイトル不明"
    return t


def fix_files() -> None:
    if os.path.exists(MAP_PATH):
        with open(MAP_PATH, "r", encoding="utf-8") as f:
            manga_map = json.load(f)
        for _key, entry in manga_map.items():
            if isinstance(entry, dict) and "title" in entry:
                entry["title"] = clean_title(entry.get("title"))
        with open(MAP_PATH, "w", encoding="utf-8") as f:
            json.dump(manga_map, f, ensure_ascii=False, indent=2)
        print(f"✅ {MAP_PATH} のタイトルを修復しました（title キーがある場合）", flush=True)

    if os.path.exists(CHAR_PATH):
        with open(CHAR_PATH, "r", encoding="utf-8") as f:
            chars = json.load(f)
        for char in chars:
            apps = char.get("appearances")
            if not isinstance(apps, list):
                continue
            for app in apps:
                if isinstance(app, dict) and "title" in app:
                    app["title"] = clean_title(app.get("title"))
        with open(CHAR_PATH, "w", encoding="utf-8") as f:
            json.dump(chars, f, ensure_ascii=False, indent=2)
        print(f"✅ {CHAR_PATH} の登場履歴タイトルを修復しました", flush=True)


if __name__ == "__main__":
    fix_files()
