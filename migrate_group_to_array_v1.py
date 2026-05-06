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
        g = c.get("group")
        if isinstance(g, list):
            # normalize: remove empties + dedupe preserve
            out: list[str] = []
            seen: set[str] = set()
            for x in g:
                if not isinstance(x, str):
                    continue
                t = x.strip()
                if not t or t in seen:
                    continue
                seen.add(t)
                out.append(t)
            if out != g:
                c["group"] = out
                changed += 1
            continue
        if isinstance(g, str):
            t = g.strip()
            c["group"] = [t] if t else []
            changed += 1
            continue
        if g is None:
            c["group"] = []
            changed += 1
            continue

        # fallback for unexpected types
        c["group"] = []
        changed += 1

    chars.sort(key=lambda x: int(x.get("id", 0)) if isinstance(x, dict) else 0)
    path.write_text(json.dumps(chars, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"migrated_group_to_array: changed={changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

