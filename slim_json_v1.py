#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path


CHAR_PATH = Path("src/data/characters.json")
SKILLS_PATH = Path("src/data/skills.json")


def file_size(path: Path) -> int:
    return os.path.getsize(path)


def main() -> int:
    before_chars = file_size(CHAR_PATH)
    before_skills = file_size(SKILLS_PATH)

    chars = json.loads(CHAR_PATH.read_text(encoding="utf-8"))
    if not isinstance(chars, list):
        raise SystemExit("characters.json must be a list")

    removed_co = 0
    removed_url = 0
    for c in chars:
        if not isinstance(c, dict):
            continue
        if "coAppearances" in c:
            del c["coAppearances"]
            removed_co += 1
        if "url" in c:
            del c["url"]
            removed_url += 1

    CHAR_PATH.write_text(json.dumps(chars, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    skills = json.loads(SKILLS_PATH.read_text(encoding="utf-8"))
    if not isinstance(skills, list):
        raise SystemExit("skills.json must be a list")

    removed_desc = 0
    for s in skills:
        if not isinstance(s, dict):
            continue
        if "description" in s:
            del s["description"]
            removed_desc += 1

    SKILLS_PATH.write_text(json.dumps(skills, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    after_chars = file_size(CHAR_PATH)
    after_skills = file_size(SKILLS_PATH)

    print("slim_json_summary")
    print(f"characters_removed_coAppearances_from={removed_co}")
    print(f"characters_removed_url_from={removed_url}")
    print(f"skills_removed_description_from={removed_desc}")
    print(f"characters_bytes_before={before_chars}")
    print(f"characters_bytes_after={after_chars}")
    print(f"skills_bytes_before={before_skills}")
    print(f"skills_bytes_after={after_skills}")
    print(f"total_bytes_before={before_chars + before_skills}")
    print(f"total_bytes_after={after_chars + after_skills}")
    print(f"total_bytes_saved={(before_chars + before_skills) - (after_chars + after_skills)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

