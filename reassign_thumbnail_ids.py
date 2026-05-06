#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
from pathlib import Path


def load_chars_from_git(rev: str, repo_rel_path: str) -> list[dict]:
    out = subprocess.check_output(
        ["git", "show", f"{rev}:{repo_rel_path}"],
        text=True,
        encoding="utf-8",
        errors="strict",
    )
    data = json.loads(out)
    if not isinstance(data, list):
        raise ValueError(f"{rev}:{repo_rel_path} is not a list")
    return data


def load_chars_from_file(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path} is not a list")
    return data


def main() -> int:
    # Old IDs are taken from the last commit (before reassign_ids.py ran).
    old_rev = "HEAD"
    chars_path = "src/data/characters.json"
    thumbs_dir = Path("public/images/thumbnails")

    old_chars = load_chars_from_git(old_rev, chars_path)
    new_chars = load_chars_from_file(Path(chars_path))

    name_to_old_id: dict[str, int] = {}
    for c in old_chars:
        if not isinstance(c, dict):
            continue
        nm = c.get("name")
        if isinstance(nm, str) and nm and isinstance(c.get("id"), int):
            # If duplicates exist, keep the smallest id for deterministic behavior.
            oid = int(c["id"])
            if nm not in name_to_old_id or oid < name_to_old_id[nm]:
                name_to_old_id[nm] = oid

    name_to_new_id: dict[str, int] = {}
    for c in new_chars:
        if not isinstance(c, dict):
            continue
        nm = c.get("name")
        if isinstance(nm, str) and nm and isinstance(c.get("id"), int):
            nid = int(c["id"])
            if nm not in name_to_new_id or nid < name_to_new_id[nm]:
                name_to_new_id[nm] = nid

    # Build rename actions.
    actions: list[tuple[int, int, str]] = []
    collisions: dict[int, list[tuple[int, str]]] = {}
    for nm, old_id in name_to_old_id.items():
        new_id = name_to_new_id.get(nm)
        if new_id is None or new_id == old_id:
            continue
        actions.append((old_id, new_id, nm))
        collisions.setdefault(new_id, []).append((old_id, nm))

    # If multiple old IDs map to the same new ID, don't clobber; report and skip those.
    collision_new_ids = {nid for nid, rows in collisions.items() if len(rows) > 1}
    safe_actions = [a for a in actions if a[1] not in collision_new_ids]

    renamed = 0
    deleted_old = 0
    skipped_no_old_file = 0
    skipped_new_exists = 0
    missing_both = 0

    for old_id, new_id, nm in sorted(safe_actions, key=lambda x: (x[1], x[0])):
        old_path = thumbs_dir / f"{old_id}.webp"
        new_path = thumbs_dir / f"{new_id}.webp"

        old_exists = old_path.exists()
        new_exists = new_path.exists()

        if old_exists and not new_exists:
            old_path.rename(new_path)
            renamed += 1
            continue

        if old_exists and new_exists:
            # Prefer the already-present new thumbnail, and remove the orphaned old one.
            old_path.unlink()
            deleted_old += 1
            skipped_new_exists += 1
            continue

        if not old_exists and new_exists:
            skipped_no_old_file += 1
            continue

        missing_both += 1
        print(f"MISSING_THUMBNAIL name={nm} old_id={old_id} new_id={new_id}")

    if collision_new_ids:
        print("COLLISION_NEW_IDS (skipped to avoid clobber):")
        for nid in sorted(collision_new_ids):
            rows = collisions.get(nid, [])
            print(f"  new_id={nid} from_old={[(oid, nm) for oid, nm in rows]}")

    print("thumbnail_id_reassign_summary")
    print(f"actions_total={len(actions)}")
    print(f"actions_safe={len(safe_actions)}")
    print(f"renamed={renamed}")
    print(f"deleted_old_due_to_new_exists={deleted_old}")
    print(f"skipped_new_exists={skipped_new_exists}")
    print(f"skipped_no_old_file={skipped_no_old_file}")
    print(f"missing_both={missing_both}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

