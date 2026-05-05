#!/usr/bin/env python3
"""第65話のタイトルを「覚悟」に統一。"""
from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _same_episode(app_ep: object, ep_num: int) -> bool:
    try:
        return int(app_ep) == ep_num
    except (TypeError, ValueError):
        return False


def update_specific_title(ep_num: int, new_title: str) -> None:
    map_path = ROOT / "src" / "data" / "manga_anime_map.json"
    if map_path.exists():
        with map_path.open(encoding="utf-8") as f:
            data = json.load(f)
        key = str(ep_num)
        if key in data and isinstance(data[key], dict):
            data[key]["title"] = new_title
        with map_path.open("w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"✅ {map_path} を更新しました")

    char_path = ROOT / "src" / "data" / "characters.json"
    if char_path.exists():
        with char_path.open(encoding="utf-8") as f:
            chars = json.load(f)
        for c in chars:
            for key in ("appearances", "covers"):
                if key not in c:
                    continue
                for app in c[key]:
                    if isinstance(app, dict) and _same_episode(app.get("episode"), ep_num):
                        app["title"] = new_title
        with char_path.open("w", encoding="utf-8", newline="\n") as f:
            json.dump(chars, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"✅ {char_path} を更新しました")

    skill_path = ROOT / "src" / "data" / "skills.json"
    if skill_path.exists():
        with skill_path.open(encoding="utf-8") as f:
            skills = json.load(f)
        for s in skills:
            eps = s.get("episodes")
            if not isinstance(eps, list):
                continue
            for ep_entry in eps:
                if isinstance(ep_entry, dict) and _same_episode(ep_entry.get("episode"), ep_num):
                    ep_entry["title"] = new_title
        with skill_path.open("w", encoding="utf-8", newline="\n") as f:
            json.dump(skills, f, ensure_ascii=False, indent=2)
            f.write("\n")
        print(f"✅ {skill_path} を更新しました")


if __name__ == "__main__":
    os.chdir(ROOT)
    update_specific_title(65, "覚悟")
