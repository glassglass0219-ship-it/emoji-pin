#!/usr/bin/env python3
from __future__ import annotations

import json
import unicodedata
from pathlib import Path


SKILLS_PATH = Path("src/data/skills.json")
CHAR_PATH = Path("src/data/characters.json")


def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "").strip())


def norm_name_key(s: str) -> str:
    return nfkc(s).lower().replace(" ", "").replace("　", "")


def find_character(chars: list[dict], user: dict) -> dict | None:
    """
    Resolve user -> character.

    skills.json の users は「id」と「name」が食い違うケースがあるため、
    name が取れる場合は **名前優先**（その後に正規化名一致）とし、
    name が無い場合のみ id で引く。
    """
    uid = user.get("id")
    uname = user.get("name")

    if isinstance(uname, str) and uname.strip():
        for c in chars:
            if not isinstance(c, dict):
                continue
            if c.get("name") == uname:
                return c
        uk = norm_name_key(uname)
        for c in chars:
            if not isinstance(c, dict):
                continue
            nm = c.get("name")
            if isinstance(nm, str) and norm_name_key(nm) == uk:
                return c

    if isinstance(uid, int):
        for c in chars:
            if isinstance(c, dict) and c.get("id") == uid:
                return c
    return None


def ensure_abilities_list(c: dict) -> list:
    ab = c.get("abilities")
    if isinstance(ab, list):
        return ab
    if ab in (None, ""):
        c["abilities"] = []
        return c["abilities"]
    c["abilities"] = [ab]
    return c["abilities"]


def ability_has_id(abilities: list, skill_id: int) -> bool:
    for a in abilities:
        if isinstance(a, dict) and a.get("id") == skill_id:
            return True
    return False


def sync() -> int:
    skills = json.loads(SKILLS_PATH.read_text(encoding="utf-8"))
    chars = json.loads(CHAR_PATH.read_text(encoding="utf-8"))
    if not isinstance(skills, list) or not isinstance(chars, list):
        raise SystemExit("skills.json and characters.json must be lists")

    update_count = 0

    for skill in skills:
        if not isinstance(skill, dict):
            continue
        s_id = skill.get("id")
        s_name = skill.get("name")
        if not isinstance(s_id, int) or not isinstance(s_name, str):
            continue

        for user in skill.get("users") or []:
            if not isinstance(user, dict):
                continue
            target = find_character(chars, user)
            if not target:
                continue

            abilities = ensure_abilities_list(target)
            if ability_has_id(abilities, s_id):
                continue

            abilities.append({"id": s_id, "name": s_name})
            print(f"✅ {target['name']} に技「{s_name}」を紐付けました")
            update_count += 1

    if update_count > 0:
        print(f"\n完了！合計 {update_count} 件の紐付けを更新しました。")
    else:
        print("\n更新が必要な紐付けはありませんでした。")

    chars.sort(key=lambda x: int(x.get("id", 0)) if isinstance(x, dict) else 0)
    CHAR_PATH.write_text(
        json.dumps(chars, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(sync())
