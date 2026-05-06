#!/usr/bin/env python3
from __future__ import annotations

import io
import json
import re
import unicodedata
from pathlib import Path

import argparse
import requests
from PIL import Image, ImageOps


SOURCE_GLOBS = [
    "src/data/*_wt100_faces.json",
    "src/data/extracted/*_wt100_faces.json",
]
CORRECTIONS_PATH = Path("src/data/name_corrections.json")
CHARACTERS_PATH = Path("src/data/characters.json")
THUMBS_DIR = Path("public/images/thumbnails")

TIMEOUT_SEC = 30
SIZE = 400
WEBP_QUALITY = 82


def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "").strip())


_SPACE_RE = re.compile(r"[ \t\u3000]+")


def norm_name(s: str) -> str:
    t = nfkc(s)
    t = _SPACE_RE.sub("", t)
    t = t.lower()
    for ch in ["・", "･", "“", "”", "〝", "〟", "「", "」", "『", "』", "｢", "｣"]:
        t = t.replace(ch, "")
    return t


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_source_files() -> list[Path]:
    files: list[Path] = []
    for g in SOURCE_GLOBS:
        files.extend(Path().glob(g))
    # uniq
    uniq: dict[str, Path] = {str(p): p for p in files}
    return list(uniq.values())


def build_source_index(source_files: list[Path]) -> dict[str, str]:
    """
    Returns map: normalized_name -> url
    If duplicates exist, the first seen wins (sources are largely consistent).
    """
    idx: dict[str, str] = {}
    for p in sorted(source_files, key=lambda x: str(x).lower()):
        try:
            data = load_json(p)
        except Exception as e:
            print(f"SKIP_BAD_JSON {p}: {e}")
            continue
        if not isinstance(data, list):
            continue
        for row in data:
            if not isinstance(row, dict):
                continue
            name = row.get("name")
            url = row.get("url")
            if not isinstance(name, str) or not isinstance(url, str):
                continue
            key = norm_name(name)
            if key and key not in idx:
                idx[key] = url
    return idx


def invert_corrections(corrections: dict) -> dict[str, set[str]]:
    """
    Build reverse map: canonical_name -> {source_name_variants}
    from both renames and merges.
    """
    reverse: dict[str, set[str]] = {}

    def add(dst: str, src: str) -> None:
        if not dst or not src:
            return
        reverse.setdefault(dst, set()).add(src)

    renames = corrections.get("renames") if isinstance(corrections, dict) else {}
    merges = corrections.get("merges") if isinstance(corrections, dict) else {}

    if isinstance(renames, dict):
        for src, dst in renames.items():
            if isinstance(src, str) and isinstance(dst, str):
                add(dst, src)

    if isinstance(merges, dict):
        for src, dst in merges.items():
            if isinstance(src, str) and isinstance(dst, str):
                add(dst, src)

    return reverse


def candidate_source_names(char_name: str, reverse_map: dict[str, set[str]]) -> list[str]:
    cands = [char_name]
    for v in sorted(reverse_map.get(char_name, set())):
        cands.append(v)
    return cands


def download_image(url: str) -> bytes:
    r = requests.get(url, timeout=TIMEOUT_SEC)
    r.raise_for_status()
    return r.content


def convert_to_webp_400(img_bytes: bytes) -> bytes:
    im = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    im = ImageOps.fit(im, (SIZE, SIZE), method=Image.LANCZOS)
    out = io.BytesIO()
    im.save(out, format="WEBP", quality=WEBP_QUALITY, method=6)
    return out.getvalue()


def cleanup_orphan_thumbnails(valid_ids: set[int]) -> int:
    if not THUMBS_DIR.exists():
        return 0
    removed = 0
    for p in THUMBS_DIR.glob("*.webp"):
        stem = p.stem
        try:
            fid = int(stem)
        except Exception:
            continue
        if fid not in valid_ids:
            p.unlink()
            removed += 1
    return removed


def main() -> int:
    ap = argparse.ArgumentParser(description="Recover thumbnails from *_wt100_faces.json by name matching.")
    ap.add_argument("--scan-only", action="store_true", help="Only compute matching/missing; do not download images.")
    ap.add_argument(
        "--source-file",
        action="append",
        default=[],
        help="Use only this source JSON file (repeatable). If provided, SOURCE_GLOBS are ignored.",
    )
    ap.add_argument(
        "--only-names-file",
        default="",
        help="If set, only process characters whose name is listed (one per line).",
    )
    ap.add_argument(
        "--missing-out",
        default="image_recovery_missing_names.txt",
        help="Output path for missing names (scan-only or full run).",
    )
    args = ap.parse_args()

    if not CHARACTERS_PATH.exists():
        raise SystemExit(f"missing {CHARACTERS_PATH}")
    if not CORRECTIONS_PATH.exists():
        raise SystemExit(f"missing {CORRECTIONS_PATH}")

    chars = load_json(CHARACTERS_PATH)
    if not isinstance(chars, list):
        raise SystemExit("characters.json must be a list")

    only_names: set[str] | None = None
    if args.only_names_file:
        only_names = set(
            n.strip()
            for n in Path(args.only_names_file).read_text(encoding="utf-8").splitlines()
            if n.strip()
        )

    corrections = load_json(CORRECTIONS_PATH)
    reverse_map = invert_corrections(corrections if isinstance(corrections, dict) else {})

    if args.source_file:
        source_files = [Path(p) for p in args.source_file]
    else:
        source_files = iter_source_files()
    if not source_files:
        raise SystemExit("no *_wt100_faces.json files found")
    source_idx = build_source_index(source_files)

    THUMBS_DIR.mkdir(parents=True, exist_ok=True)

    updated = 0
    missing: list[str] = []
    download_failed: list[str] = []

    # Build id set for cleanup
    valid_ids: set[int] = set()
    for c in chars:
        if isinstance(c, dict) and isinstance(c.get("id"), int):
            valid_ids.add(int(c["id"]))

    for i, c in enumerate(chars, start=1):
        if not isinstance(c, dict):
            continue
        cid = c.get("id")
        name = c.get("name")
        if not isinstance(cid, int) or not isinstance(name, str) or not name:
            continue
        if only_names is not None and name not in only_names:
            continue

        url = None
        for cand in candidate_source_names(name, reverse_map):
            url = source_idx.get(norm_name(cand))
            if url:
                break

        if not url:
            missing.append(name)
            continue

        if args.scan_only:
            updated += 1
            if i % 200 == 0:
                print(f"progress(scan) {i}/{len(chars)} matched={updated} missing={len(missing)}")
            continue

        try:
            webp = convert_to_webp_400(download_image(url))
        except Exception as e:
            download_failed.append(f"{name} ({url}) error={e}")
            continue

        (THUMBS_DIR / f"{cid}.webp").write_bytes(webp)
        updated += 1

        if i % 100 == 0:
            print(f"progress {i}/{len(chars)} updated={updated} missing={len(missing)} failed={len(download_failed)}")

    removed = 0 if args.scan_only else cleanup_orphan_thumbnails(valid_ids)

    print("image_recovery_summary")
    print(f"source_files={len(source_files)}")
    print(f"updated={updated}")
    print(f"missing_match_count={len(missing)}")
    print(f"download_failed_count={len(download_failed)}")
    print(f"orphan_thumbnails_removed={removed}")

    if missing:
        out_path = Path(args.missing_out)
        out_path.write_text("\n".join(missing) + "\n", encoding="utf-8")
        print(f"missing_names_written_to={out_path}")
        print("missing_match_names:")
        for n in missing:
            print(f"- {n}")

    if download_failed:
        print("download_failed:")
        for row in download_failed[:200]:
            print(row)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

