#!/usr/bin/env python3
"""Remove 拳骨衝撃 from Garp; set debut episodes on 拳骨衝突/拳骨流星群/無限拳骨; drop orphan skill 1179."""

from __future__ import annotations

import json
from pathlib import Path

CHAR_PATH = Path("src/data/characters.json")
MAP_PATH = Path("src/data/manga_anime_map.json")
SKILLS_PATH = Path("src/data/skills.json")

GARP_ID = 443
GARP_NAME = "モンキー・Ｄ・ガープ"
REMOVE_SKILL_ID = 1179  # 拳骨衝撃（誤・ガープから削除）
EPISODE_UPDATES = {
    1204: ("拳骨流星群", 438),
    1205: ("拳骨衝突", 1080),
    1207: ("無限拳骨", 1165),
}


def _title_from_map(m: dict, ep: int) -> str:
    key = str(ep)
    if key not in m:
        return ""
    entry = m[key]
    if isinstance(entry, dict) and isinstance(entry.get("title"), str):
        return entry["title"]
    return ""


def main() -> int:
    manga = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    chars = json.loads(CHAR_PATH.read_text(encoding="utf-8"))
    skills = json.loads(SKILLS_PATH.read_text(encoding="utf-8"))

    garp = next((c for c in chars if isinstance(c, dict) and c.get("id") == GARP_ID), None)
    if not garp or garp.get("name") != GARP_NAME:
        raise SystemExit(f"Garp not found: id={GARP_ID} name={GARP_NAME!r}")

    ab = garp.get("abilities")
    if not isinstance(ab, list):
        ab = []
    before = len(ab)
    ab = [a for a in ab if not (isinstance(a, dict) and a.get("id") == REMOVE_SKILL_ID)]
    garp["abilities"] = ab
    removed_abil = before - len(ab)

    by_id = {s["id"]: s for s in skills if isinstance(s, dict) and "id" in s}

    for sid, (expect_name, ep) in EPISODE_UPDATES.items():
        s = by_id.get(sid)
        if not s:
            raise SystemExit(f"skill id {sid} not found")
        if s.get("name") != expect_name:
            raise SystemExit(f"skill {sid}: expected name {expect_name!r}, got {s.get('name')!r}")
        title = _title_from_map(manga, ep)
        s["episodes"] = [{"episode": ep, "title": title}]

    skills = [s for s in skills if not (isinstance(s, dict) and s.get("id") == REMOVE_SKILL_ID)]
    if REMOVE_SKILL_ID in {s.get("id") for s in skills if isinstance(s, dict)}:
        raise SystemExit("skill 1179 still present after filter")

    CHAR_PATH.write_text(
        json.dumps(chars, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    SKILLS_PATH.write_text(
        json.dumps(skills, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )

    print(f"garp abilities removed id={REMOVE_SKILL_ID}: {removed_abil}")
    for sid, (_, ep) in EPISODE_UPDATES.items():
        t = by_id[sid]["episodes"][0].get("title", "")
        print(f"skill {sid} episode {ep} title={t!r}")
    print("removed skill entry id=1179 from skills.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
