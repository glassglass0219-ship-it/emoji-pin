#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import requests
from PIL import Image

import sync_images as si
import sync_images_v3 as v3


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return list(r)


def download_to_webp(session: requests.Session, url: str, out_path: Path) -> None:
    resp = session.get(url, timeout=90)
    resp.raise_for_status()
    im = Image.open(io.BytesIO(resp.content))
    im = im.convert("RGBA")
    im = im.resize((400, 400), Image.Resampling.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    im.save(out_path, format="WEBP", quality=80, method=6)


def new_character_stub_v4(cid: int, name: str) -> dict[str, Any]:
    """
    現在の characters.json 構造に合わせたスタブ。
    """
    return {
        "id": cid,
        "name": name,
        "reading": "",
        "gender": "",
        "devilFruit": "",
        "bounty": "",
        "birthday": "",
        "firstAppearance": "",
        "appearances": [],
        "covers": [],
        "abilities": [],
        "coAppearances": [],
        "alias": "",
        "en_name": "",
        "arcs": [],
        "category": "",
        "group": "",
    }


def find_char_by_id(chars: list[dict[str, Any]], cid: int) -> dict[str, Any] | None:
    for c in chars:
        if not isinstance(c, dict):
            continue
        try:
            if int(c.get("id")) == cid:
                return c
        except Exception:
            continue
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Egghead 名寄せ解除（variants分離）+ 再同期")
    ap.add_argument("--arc-name", default="エッグヘッド編")
    ap.add_argument("--characters", default="src/data/characters.json")
    ap.add_argument("--source", default="src/data/extracted/egghead_wt100_faces.json")
    ap.add_argument("--collisions", default="egghead_id_collisions.csv")
    ap.add_argument("--sleep", type=float, default=0.22)
    args = ap.parse_args()

    arc_name = str(args.arc_name).strip()
    os.chdir(si.ROOT)

    chars_path = Path(args.characters)
    source_path = v3.resolve_source_path(Path(args.source))
    collisions_path = Path(args.collisions)

    faces = v3.load_faces_json(source_path)
    collisions = load_csv_rows(collisions_path)

    chars: list[dict[str, Any]] = json.loads(chars_path.read_text(encoding="utf-8"))
    si.ensure_arcs_field(chars)

    max_id = 0
    for c in chars:
        if not isinstance(c, dict):
            continue
        try:
            max_id = max(max_id, int(c.get("id") or 0))
        except Exception:
            continue

    # group collisions
    by_master: dict[int, list[dict[str, str]]] = defaultdict(list)
    for r in collisions:
        try:
            mid = int(r["master_id"])
        except Exception:
            continue
        by_master[mid].append(r)

    session = requests.Session()
    session.headers.update({"User-Agent": si.CHROME_UA})

    created: list[dict[str, Any]] = []
    downloaded_ok = 0
    downloaded_fail = 0
    failures: list[dict[str, Any]] = []

    # 1) collisions 解消（親IDから切り離して新規ID化）
    for master_id, rows in sorted(by_master.items(), key=lambda x: x[0]):
        master = find_char_by_id(chars, master_id)
        if master is None:
            continue
        master_name = str(master.get("name") or "")

        # keep row: resolved == master_name or source_name == master_name（NFKC）
        keep_idx = None
        for i, r in enumerate(rows):
            if v3.nfkc(r.get("resolved", "")) == v3.nfkc(master_name) or v3.nfkc(r.get("source_name", "")) == v3.nfkc(master_name):
                keep_idx = i
                break
        if keep_idx is None:
            keep_idx = 0

        # ensure parent has arc
        si.append_arc_unique(master, arc_name)

        for i, r in enumerate(rows):
            if i == keep_idx:
                continue
            try:
                src_index = int(r["source_index"])
            except Exception:
                continue
            resolved = r.get("resolved", "").strip()
            if not resolved:
                continue

            max_id += 1
            new_id = max_id
            new_char = new_character_stub_v4(new_id, resolved)
            si.append_arc_unique(new_char, arc_name)
            chars.append(new_char)
            created.append({"new_id": new_id, "name": resolved, "from_master": master_id, "master_name": master_name})

            # download image
            try:
                face = faces[src_index]
                url = str(face.get("url") or "").strip()
                out_p = si.PUBLIC_THUMB / f"{new_id}.webp"
                if not out_p.exists():
                    download_to_webp(session, url, out_p)
                    downloaded_ok += 1
            except Exception as e:
                downloaded_fail += 1
                failures.append({"new_id": new_id, "name": resolved, "error": repr(e)})

            time.sleep(max(0.0, args.sleep))

    # 2) 再同期（strict keywords は exact 以外は新規）
    #    目的: 残っている variants を吸収せずに必要なら新規作成し、arc を保証する
    updated_existing = 0
    added_new = 0

    # name->char exact map (NFKC)
    def exact_lookup(name: str) -> dict[str, Any] | None:
        target = v3.nfkc(name)
        for c in chars:
            if not isinstance(c, dict):
                continue
            if v3.nfkc(str(c.get("name") or "")) == target:
                return c
        return None

    for row in faces:
        src_name = str(row.get("name") or "").strip()
        url = str(row.get("url") or "").strip()

        # mergesはここでは不要（extractedはすでに整形済み前提）
        resolved = src_name
        strict = v3.is_strict_variant_name(resolved)

        if strict:
            ch = exact_lookup(resolved)
        else:
            renames = si.load_renames(si.CORRECTIONS_PATH)
            ch = si.find_character(chars, resolved, "", renames)
            if ch is None:
                m = v3.best_match_for_name(chars, resolved, renames)
                if m is not None:
                    ch = m.char

        if ch is None:
            max_id += 1
            ch = new_character_stub_v4(max_id, resolved)
            chars.append(ch)
            added_new += 1

        si.append_arc_unique(ch, arc_name)
        updated_existing += 1

        cid = int(ch["id"])
        out_p = si.PUBLIC_THUMB / f"{cid}.webp"
        if not out_p.exists():
            try:
                download_to_webp(session, url, out_p)
                downloaded_ok += 1
            except Exception as e:
                downloaded_fail += 1
                failures.append({"id": cid, "name": str(ch.get("name") or ""), "error": repr(e)})
            time.sleep(max(0.0, args.sleep))

    # save characters
    chars.sort(key=lambda x: int(str(x.get("id", 0)) or 0) if isinstance(x, dict) else 0)
    chars_path.write_text(json.dumps(chars, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    # count arc
    arc_count = 0
    for c in chars:
        if not isinstance(c, dict):
            continue
        arcs = c.get("arcs")
        if isinstance(arcs, list) and arc_name in arcs:
            arc_count += 1

    print(f"created_from_collisions: {len(created)}")
    if created:
        print("created list:")
        for r in created:
            print(f"  - id={r['new_id']} name={r['name']!r} (from {r['from_master']} {r['master_name']!r})")
    print(f"resync_updated_rows: {updated_existing}")
    print(f"resync_added_new: {added_new}")
    print(f"image_download_ok: {downloaded_ok}")
    print(f"image_download_fail: {downloaded_fail}")
    if failures:
        print("failures:")
        for r in failures[:50]:
            print(f"  - {r}")
        if len(failures) > 50:
            print(f"  ... and {len(failures) - 50} more")
    print(f"final_arc_count('{arc_name}'): {arc_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

