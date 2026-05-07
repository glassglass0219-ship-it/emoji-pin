#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


SKILLS_PATH = Path("src/data/skills.json")
CHARS_PATH = Path("src/data/characters.json")
UPDATES_PATH = Path("src/data/updates.json")


def find_char_id(chars: list, name: str) -> int | None:
    for c in chars:
        if isinstance(c, dict) and c.get("name") == name:
            cid = c.get("id")
            if isinstance(cid, int):
                return cid
    return None


def main() -> int:
    skills = json.loads(SKILLS_PATH.read_text(encoding="utf-8"))
    if not isinstance(skills, list):
        raise SystemExit("skills.json must be a list")

    chars = json.loads(CHARS_PATH.read_text(encoding="utf-8"))
    if not isinstance(chars, list):
        raise SystemExit("characters.json must be a list")

    roger_name = "ゴール・Ｄ・ロジャー"
    rayleigh_name = "シルバーズ・レイリー"

    roger_id = find_char_id(chars, roger_name)
    rayleigh_id = find_char_id(chars, rayleigh_name)
    if roger_id is None or rayleigh_id is None:
        raise SystemExit(f"missing char ids: roger={roger_id}, rayleigh={rayleigh_id}")

    existing_ids = [s.get("id") for s in skills if isinstance(s.get("id"), int)]
    next_id = (max(existing_ids) if existing_ids else 0) + 1

    new_skills = [
        {
            "id": next_id,
            "name": "荒御魂",
            "reading": "アラミタマ",
            "users": [{"id": roger_id, "name": roger_name}],
            "episodes": [{"episode": 1156, "title": "アイドル"}],
            "en_name": "",
        },
        {
            "id": next_id + 1,
            "name": "彼岸刃鉈",
            "reading": "ヒガンバナ",
            "users": [{"id": rayleigh_id, "name": rayleigh_name}],
            "episodes": [{"episode": 1161, "title": "矢の雨をしのいで結ぶ恋の詩"}],
            "en_name": "",
        },
        {
            "id": next_id + 2,
            "name": "火之迦具土慧士",
            "reading": "ヒノカグツチノエイス",
            "users": [{"id": roger_id, "name": roger_name}],
            "episodes": [{"episode": 1165, "title": "残響"}],
            "en_name": "",
        },
    ]

    name_set = {(s.get("name"), s.get("reading")) for s in skills if isinstance(s, dict)}
    added = []
    for ns in new_skills:
        key = (ns["name"], ns["reading"])
        if key in name_set:
            continue
        skills.append(ns)
        added.append(ns["id"])

    SKILLS_PATH.write_text(
        json.dumps(skills, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    updates = json.loads(UPDATES_PATH.read_text(encoding="utf-8")) if UPDATES_PATH.exists() else []
    if not isinstance(updates, list):
        raise SystemExit("updates.json must be a list")

    new_entry = {
        "date": "2026-05-07",
        "content": "伝説の世代 <b>【ロジャー・レイリー】</b> の最新の技情報を反映",
        "type": "update",
    }
    duplicate = any(
        isinstance(u, dict)
        and u.get("date") == new_entry["date"]
        and u.get("content") == new_entry["content"]
        for u in updates
    )
    if not duplicate:
        updates.insert(0, new_entry)

    UPDATES_PATH.write_text(
        json.dumps(updates, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    print(f"added_skill_ids={added}")
    print(f"updates_total={len(updates)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
