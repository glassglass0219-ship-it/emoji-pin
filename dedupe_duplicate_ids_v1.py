#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


CHARACTERS_PATH = Path("src/data/characters.json")


LIST_FIELDS = {"appearances", "arcs", "abilities", "covers", "coAppearances", "category", "group"}


def uniq_list(seq: list) -> list:
    out = []
    seen = set()
    for x in seq:
        key = json.dumps(x, ensure_ascii=False, sort_keys=True) if isinstance(x, (dict, list)) else str(x)
        if key in seen:
            continue
        seen.add(key)
        out.append(x)
    return out


def merge_two(a: dict, b: dict) -> dict:
    """
    Merge b into a (non-destructive for information):
    - Scalars: keep a's value if truthy/non-empty; otherwise take b's.
    - Lists: union with de-duplication (for appearances we dedupe by episode if possible).
    """
    out = dict(a)

    for k, bv in b.items():
        av = out.get(k)
        if k in LIST_FIELDS:
            al = av if isinstance(av, list) else ([] if av in (None, "") else [av])
            bl = bv if isinstance(bv, list) else ([] if bv in (None, "") else [bv])

            if k == "appearances":
                merged = []
                by_ep = {}
                for row in (al + bl):
                    if isinstance(row, dict) and isinstance(row.get("episode"), int):
                        ep = row["episode"]
                        # prefer the one that has a title
                        prev = by_ep.get(ep)
                        if not prev or (not prev.get("title") and row.get("title")):
                            by_ep[ep] = row
                    else:
                        merged.append(row)
                merged.extend(by_ep[ep] for ep in sorted(by_ep.keys()))
                out[k] = uniq_list(merged)
            else:
                out[k] = uniq_list(al + bl)
            continue

        # Scalars / objects: keep existing if meaningful, otherwise take from b.
        if av is None or av == "" or av == []:
            out[k] = bv

    return out


def main() -> int:
    chars = json.loads(CHARACTERS_PATH.read_text(encoding="utf-8"))
    if not isinstance(chars, list):
        raise SystemExit("characters.json must be a list")

    by_id: dict[int, dict] = {}
    dup_ids: set[int] = set()

    for c in chars:
        if not isinstance(c, dict):
            continue
        cid = c.get("id")
        if not isinstance(cid, int):
            continue
        if cid in by_id:
            dup_ids.add(cid)
            by_id[cid] = merge_two(by_id[cid], c)
        else:
            by_id[cid] = c

    out_chars = list(by_id.values())
    out_chars.sort(key=lambda x: int(x.get("id", 0)) if isinstance(x, dict) else 0)
    CHARACTERS_PATH.write_text(json.dumps(out_chars, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    print(f"dedupe_done total_in={len(chars)} total_out={len(out_chars)} dup_id_count={len(dup_ids)}")
    if dup_ids:
        print("dup_ids:", ",".join(str(x) for x in sorted(dup_ids)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

