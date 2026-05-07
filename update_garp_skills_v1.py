#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


SKILLS_PATH = Path("src/data/skills.json")
CHAR_PATH = Path("src/data/characters.json")


GARP_NAME = "モンキー・Ｄ・ガープ"


READING_UPDATES: list[tuple[str, str]] = [
    ("拳骨隕石", "ゲンコツメテオ"),
    ("海底落下", "ブルーホール"),
    ("拳骨唐竹割", "ギャラクシーディバイド"),
]

NEW_SKILLS: list[tuple[str, str]] = [
    ("拳骨流星群", "ゲンコツりゅうせいぐん"),
    ("拳骨衝突", "ギャラクシーインパクト"),
    ("海賊火の玉", "カイゾクヒノタマ"),
    ("無限拳骨", "インフィニトゥムエクスプロージョン"),
]


def main() -> int:
    skills = json.loads(SKILLS_PATH.read_text(encoding="utf-8"))
    chars = json.loads(CHAR_PATH.read_text(encoding="utf-8"))
    if not isinstance(skills, list) or not isinstance(chars, list):
        raise SystemExit("skills.json/characters.json must be lists")

    garp = next((c for c in chars if isinstance(c, dict) and c.get("name") == GARP_NAME), None)
    if not garp:
        raise SystemExit(f"character not found: {GARP_NAME}")
    garp_id = int(garp["id"])

    by_name: dict[str, dict] = {}
    for s in skills:
        if isinstance(s, dict) and isinstance(s.get("name"), str):
            by_name.setdefault(s["name"], s)

    updated_readings: list[tuple[int, str, str, str]] = []
    for name, new_reading in READING_UPDATES:
        s = by_name.get(name)
        if not s:
            print(f"WARN reading-update: skill not found name={name}")
            continue
        old = s.get("reading")
        if old == new_reading:
            print(f"SKIP reading-update: name={name} reading already={new_reading}")
            continue
        s["reading"] = new_reading
        updated_readings.append((int(s.get("id", 0)), name, str(old or ""), new_reading))

    existing_ids = [s.get("id") for s in skills if isinstance(s.get("id"), int)]
    next_id = (max(existing_ids) if existing_ids else 0) + 1

    added: list[tuple[int, str, str]] = []
    for name, reading in NEW_SKILLS:
        if name in by_name:
            print(f"SKIP add: {name} already exists id={by_name[name].get('id')}")
            continue
        new_skill = {
            "id": next_id,
            "name": name,
            "reading": reading,
            "users": [{"id": garp_id, "name": GARP_NAME}],
            "episodes": [],
            "en_name": "",
        }
        skills.append(new_skill)
        added.append((next_id, name, reading))
        next_id += 1

    SKILLS_PATH.write_text(
        json.dumps(skills, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    abilities = garp.get("abilities")
    if not isinstance(abilities, list):
        abilities = []
        garp["abilities"] = abilities

    have_ids = {a.get("id") for a in abilities if isinstance(a, dict)}
    new_links: list[tuple[int, str]] = []

    for sid, name, _ in added:
        if sid in have_ids:
            continue
        abilities.append({"id": sid, "name": name})
        have_ids.add(sid)
        new_links.append((sid, name))

    for sid, name, _, _ in updated_readings:
        if sid in have_ids:
            continue
        abilities.append({"id": sid, "name": name})
        have_ids.add(sid)
        new_links.append((sid, name))

    chars.sort(key=lambda x: int(x.get("id", 0)) if isinstance(x, dict) else 0)
    CHAR_PATH.write_text(
        json.dumps(chars, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    print("garp_skill_update_summary")
    print(f"reading_updates_done={len(updated_readings)}")
    for sid, name, old, new in updated_readings:
        print(f"READING id={sid} name={name} {old} -> {new}")
    print(f"new_skills_added={len(added)}")
    for sid, name, reading in added:
        print(f"NEW id={sid} name={name} reading={reading}")
    print(f"abilities_linked_added_to_garp={len(new_links)}")
    for sid, name in new_links:
        print(f"LINK garp+={sid} name={name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
