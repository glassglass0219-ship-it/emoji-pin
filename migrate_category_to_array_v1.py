#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


def main() -> int:
    path = Path("src/data/characters.json")
    chars = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(chars, list):
        raise SystemExit("characters.json must be a list")

    changed = 0
    for c in chars:
        if not isinstance(c, dict):
            continue
        v = c.get("category")
        if isinstance(v, list):
            out: list[str] = []
            seen: set[str] = set()
            for x in v:
                if not isinstance(x, str):
                    continue
                t = x.strip()
                if not t or t in seen:
                    continue
                seen.add(t)
                out.append(t)
            if out != v:
                c["category"] = out
                changed += 1
            continue
        if isinstance(v, str):
            t = v.strip()
            c["category"] = [t] if t else []
            changed += 1
            continue
        if v is None:
            c["category"] = []
            changed += 1
            continue
        c["category"] = []
        changed += 1

    chars.sort(key=lambda x: int(x.get("id", 0)) if isinstance(x, dict) else 0)
    path.write_text(json.dumps(chars, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"migrated_category_to_array: changed={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

