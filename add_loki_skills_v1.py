#!/usr/bin/env python3
"""Add 3 new skills to skills.json and link to ロキ (id=1516)."""

from __future__ import annotations

import json
from pathlib import Path

CHAR_PATH = Path("src/data/characters.json")
MAP_PATH = Path("src/data/manga_anime_map.json")
SKILLS_PATH = Path("src/data/skills.json")

LOKI_ID = 1516
LOKI_NAME = "ロキ"


def _title(manga: dict, ep: int) -> str:
    e = manga.get(str(ep))
    if isinstance(e, dict) and isinstance(e.get("title"), str):
        return e["title"]
    return ""


def main() -> int:
    manga = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    chars = json.loads(CHAR_PATH.read_text(encoding="utf-8"))
    skills = json.loads(SKILLS_PATH.read_text(encoding="utf-8"))

    loki = next((c for c in chars if isinstance(c, dict) and c.get("id") == LOKI_ID), None)
    if not loki or loki.get("name") != LOKI_NAME:
        raise SystemExit(f"Loki not found: id={LOKI_ID} name={LOKI_NAME!r}")

    new_skills = [
        {
            "name": "原初世界",
            "reading": "ニブルヘイム",
            "episode": 1171,
        },
        {
            "name": "雷界",
            "reading": "トールヘイム",
            "episode": None,
        },
        {
            "name": "鉄雷一槌",
            "reading": "ラグナイヅチ",
            "episode": None,
        },
    ]

    by_name = {s.get("name"): s for s in skills if isinstance(s, dict)}
    next_id = max(s["id"] for s in skills if isinstance(s, dict) and isinstance(s.get("id"), int)) + 1

    abilities = loki.get("abilities")
    if not isinstance(abilities, list):
        abilities = []
        loki["abilities"] = abilities
    have_ids = {a.get("id") for a in abilities if isinstance(a, dict)}

    added = []
    for spec in new_skills:
        name = spec["name"]
        if name in by_name:
            print(f"SKIP exists name={name} id={by_name[name].get('id')}")
            continue
        ep = spec["episode"]
        episodes = []
        if isinstance(ep, int):
            episodes = [{"episode": ep, "title": _title(manga, ep)}]
        sk = {
            "id": next_id,
            "name": name,
            "reading": spec["reading"],
            "users": [{"id": LOKI_ID, "name": LOKI_NAME}],
            "episodes": episodes,
            "en_name": "",
        }
        skills.append(sk)
        added.append(sk)
        if next_id not in have_ids:
            abilities.append({"id": next_id, "name": name})
            have_ids.add(next_id)
        next_id += 1

    SKILLS_PATH.write_text(
        json.dumps(skills, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    CHAR_PATH.write_text(
        json.dumps(chars, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    print(f"added {len(added)} skill(s)")
    for s in added:
        print(f"  id={s['id']} name={s['name']} reading={s['reading']} episodes={s['episodes']}")
    print(f"Loki abilities now: {[(a.get('id'), a.get('name')) for a in abilities]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
