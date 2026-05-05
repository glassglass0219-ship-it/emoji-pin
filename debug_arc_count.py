#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import sync_images as si
import sync_images_v3 as v3


def main() -> int:
    ap = argparse.ArgumentParser(description="egghead取り込み件数差分の調査")
    ap.add_argument("--arc-name", default="エッグヘッド編")
    ap.add_argument("--source", default="src/data/extracted/egghead_wt100_faces.json")
    ap.add_argument("--characters", default="src/data/characters.json")
    ap.add_argument("--output-mapping", default="egghead_source_to_master_mapping.csv")
    ap.add_argument("--output-collisions", default="egghead_id_collisions.csv")
    ap.add_argument("--output-missing-arc", default="egghead_missing_arc.csv")
    args = ap.parse_args()

    arc_name = str(args.arc_name).strip()
    source_path = v3.resolve_source_path(Path(args.source))
    chars_path = Path(args.characters)

    faces = v3.load_faces_json(source_path)
    merges = v3.load_merges(si.CORRECTIONS_PATH)
    renames = si.load_renames(si.CORRECTIONS_PATH)

    chars: list[dict[str, Any]] = json.loads(chars_path.read_text(encoding="utf-8"))
    si.ensure_arcs_field(chars)

    mapping_rows: list[dict[str, Any]] = []
    id_to_sources: dict[int, list[dict[str, Any]]] = defaultdict(list)
    missing_arc: list[dict[str, Any]] = []
    unmatched: list[dict[str, Any]] = []

    for i, row in enumerate(faces):
        src_name = str(row.get("name") or "").strip()
        url = str(row.get("url") or "").strip()
        resolved = v3.resolve_merge_display(src_name, merges)

        # v2のfind_character -> v3 fuzzy fallback と同じ順
        ch = si.find_character(chars, resolved, "", renames)
        reason = "si.find_character"
        score = ""
        if ch is None:
            m = v3.best_match_for_name(chars, resolved, renames)
            if m is not None:
                ch = m.char
                reason = f"v3.fuzzy:{m.reason}"
                score = f"{m.score:.2f}"

        if ch is None:
            unmatched.append({"index": i, "source_name": src_name, "resolved": resolved, "url": url})
            mapping_rows.append(
                {
                    "index": i,
                    "source_name": src_name,
                    "resolved": resolved,
                    "matched": False,
                    "master_id": "",
                    "master_name": "",
                    "reason": "unmatched",
                    "score": "",
                    "has_arc": "",
                }
            )
            continue

        cid = int(ch.get("id"))
        master_name = str(ch.get("name") or "")
        arcs = ch.get("arcs") if isinstance(ch.get("arcs"), list) else []
        has_arc = arc_name in arcs

        mapping_rows.append(
            {
                "index": i,
                "source_name": src_name,
                "resolved": resolved,
                "matched": True,
                "master_id": cid,
                "master_name": master_name,
                "reason": reason,
                "score": score,
                "has_arc": has_arc,
            }
        )
        id_to_sources[cid].append(
            {
                "index": i,
                "source_name": src_name,
                "resolved": resolved,
                "url": url,
                "reason": reason,
                "score": score,
            }
        )
        if not has_arc:
            missing_arc.append(
                {
                    "index": i,
                    "source_name": src_name,
                    "resolved": resolved,
                    "master_id": cid,
                    "master_name": master_name,
                    "reason": reason,
                    "score": score,
                }
            )

    # collisions: same master_id has 2+ source rows
    collisions: list[dict[str, Any]] = []
    for cid, rows in sorted(id_to_sources.items(), key=lambda x: x[0]):
        if len(rows) <= 1:
            continue
        # include master name
        master = next((c for c in chars if int(c.get("id", -1)) == cid), None)
        master_name = str(master.get("name") or "") if isinstance(master, dict) else ""
        for r in rows:
            collisions.append(
                {
                    "master_id": cid,
                    "master_name": master_name,
                    "source_index": r["index"],
                    "source_name": r["source_name"],
                    "resolved": r["resolved"],
                    "reason": r["reason"],
                    "score": r["score"],
                }
            )

    # write CSVs (utf-8-sig)
    def write_csv(path: Path, header: list[str], rows: list[dict[str, Any]]) -> None:
        with path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=header)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in header})

    write_csv(
        Path(args.output_mapping),
        ["index", "source_name", "resolved", "matched", "master_id", "master_name", "reason", "score", "has_arc"],
        mapping_rows,
    )
    write_csv(
        Path(args.output_collisions),
        ["master_id", "master_name", "source_index", "source_name", "resolved", "reason", "score"],
        collisions,
    )
    write_csv(
        Path(args.output_missing_arc),
        ["index", "source_name", "resolved", "master_id", "master_name", "reason", "score"],
        missing_arc,
    )

    matched = sum(1 for r in mapping_rows if r["matched"])
    unique_ids = len(id_to_sources)
    collision_rows = sum(max(0, len(v) - 1) for v in id_to_sources.values())

    print(f"source rows (faces png): {len(faces)}")
    print(f"matched rows: {matched}")
    print(f"unmatched rows: {len(unmatched)}")
    print(f"unique master ids matched: {unique_ids}")
    print(f"collisions (extra rows beyond uniqueness): {collision_rows}")
    print(f"missing arc '{arc_name}' among matched: {len(missing_arc)}")
    print()
    print(f"Wrote: {args.output_mapping}")
    print(f"Wrote: {args.output_collisions}")
    print(f"Wrote: {args.output_missing_arc}")

    # conclusion helper
    if len(faces) - unique_ids == collision_rows and len(missing_arc) == 0 and len(unmatched) == 0:
        print()
        print("結論: ソース330件のうち、複数行が同一IDへ名寄せされているため、ユニークキャラ数が減っています。")
        print(f"  - 期待差分: {len(faces)} - {unique_ids} = {len(faces) - unique_ids}")
    else:
        print()
        print("結論: 名寄せ以外（未マッチ / arcs未付与）が差分に関与しています。CSVを参照してください。")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

