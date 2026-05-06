#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path


CHAR_PATH = Path("src/data/characters.json")
THUMBS_DIR = Path("public/images/thumbnails")
COVERS_DIR = Path("public/images/covers")

# PUBLISHED_LIMITS に合わせて 114 巻まで
COVER_VOLUME_LIMIT = 114


_NUM_RE = re.compile(r"^(\d+)$")


def parse_numeric_stem(p: Path) -> int | None:
    m = _NUM_RE.match(p.stem)
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


def main() -> int:
    if not CHAR_PATH.exists():
        raise SystemExit(f"missing {CHAR_PATH}")

    chars = json.loads(CHAR_PATH.read_text(encoding="utf-8"))
    if not isinstance(chars, list):
        raise SystemExit("characters.json must be a list")

    valid_ids: set[int] = set()
    for c in chars:
        if isinstance(c, dict) and isinstance(c.get("id"), int):
            valid_ids.add(int(c["id"]))

    # 1) thumbnails cleanup
    to_delete: list[Path] = []
    unknown_name: list[Path] = []

    if THUMBS_DIR.exists():
        for p in THUMBS_DIR.glob("*"):
            if not p.is_file():
                continue
            # Only manage numeric-stem image files (webp/png/jpg/etc)
            n = parse_numeric_stem(p)
            if n is None:
                unknown_name.append(p)
                continue
            if n not in valid_ids:
                to_delete.append(p)

    to_delete.sort(key=lambda x: (parse_numeric_stem(x) or 10**9, x.name))

    print(f"valid_character_ids={len(valid_ids)}")
    print(f"thumbnails_scanned_dir={THUMBS_DIR}")
    print(f"thumbnails_delete_planned={len(to_delete)}")
    if to_delete:
        sample = to_delete[:30]
        print("thumbnails_delete_sample:")
        for p in sample:
            print(f"- {p.as_posix()}")
        if len(to_delete) > len(sample):
            print(f"... and {len(to_delete) - len(sample)} more")

    # Confirmation message required by spec (non-interactive)
    print(f"\nCONFIRM: deleting {len(to_delete)} thumbnail file(s) not present in characters.json ids...")

    deleted = 0
    for p in to_delete:
        try:
            p.unlink()
            deleted += 1
        except Exception as e:
            print(f"FAILED_DELETE {p}: {e}")

    print(f"thumbnails_deleted={deleted}")

    if unknown_name:
        unknown_name.sort(key=lambda x: x.name.lower())
        print(f"thumbnails_skipped_non_numeric={len(unknown_name)}")
        for p in unknown_name[:30]:
            print(f"SKIP_NON_NUMERIC {p.as_posix()}")
        if len(unknown_name) > 30:
            print(f"... and {len(unknown_name) - 30} more")

    # 2) covers over limit report
    over_limit: list[Path] = []
    if COVERS_DIR.exists():
        for p in COVERS_DIR.glob("*"):
            if not p.is_file():
                continue
            n = parse_numeric_stem(p)
            if n is None:
                continue
            if n > COVER_VOLUME_LIMIT:
                over_limit.append(p)
    over_limit.sort(key=lambda x: (parse_numeric_stem(x) or 10**9, x.name))

    print(f"covers_dir={COVERS_DIR}")
    print(f"covers_volume_limit={COVER_VOLUME_LIMIT}")
    print(f"covers_over_limit_count={len(over_limit)}")
    for p in over_limit[:50]:
        print(f"OVER_LIMIT_COVER {p.as_posix()}")
    if len(over_limit) > 50:
        print(f"... and {len(over_limit) - 50} more")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

