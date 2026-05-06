#!/usr/bin/env python3
from __future__ import annotations

import io
import json
from pathlib import Path

import requests
from PIL import Image


ROOT = Path(__file__).resolve().parent
CHAR_PATH = ROOT / "src" / "data" / "characters.json"
THUMB_DIR = ROOT / "public" / "images" / "thumbnails"


def download_to_webp_400(url: str, out_path: Path, quality: int = 80) -> None:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    img = Image.open(io.BytesIO(r.content)).convert("RGBA")
    img = img.resize((400, 400), Image.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "WEBP", quality=quality, method=6)


def append_unique_str(lst: object, value: str) -> list[str]:
    cur = lst if isinstance(lst, list) else []
    out: list[str] = []
    seen: set[str] = set()
    for x in cur + [value]:
        if not isinstance(x, str):
            continue
        t = x.strip()
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def new_character_stub(new_id: int, name: str) -> dict:
    return {
        "id": new_id,
        "name": name,
        "reading": "",
        "gender": "",
        "devilFruit": "",
        "bounty": "",
        "birthday": "",
        "firstAppearance": "",
        "appearances": [],
        "abilities": [],
        "coAppearances": [],
        "alias": "",
        "en_name": "",
        "arcs": ["エルバフ編"],
        "category": "戦う者達",
        "group": "エルバフ",
    }


def main() -> int:
    targets = [
        ("にーずほっぐ（MMA）", "https://onepiecewt100-2026.com/assets/faces/1528.png?v=gjdgxu"),
        ("かみなり（MMA）", "https://onepiecewt100-2026.com/assets/faces/1530.png?v=gjdgxu"),
        ("おばけ（MMA）", "https://onepiecewt100-2026.com/assets/faces/1532.png?v=gjdgxu"),
    ]

    chars = json.loads(CHAR_PATH.read_text(encoding="utf-8"))
    if not isinstance(chars, list):
        raise SystemExit("characters.json must be a list")

    max_id = 0
    by_name: dict[str, dict] = {}
    for c in chars:
        if not isinstance(c, dict):
            continue
        try:
            cid = int(c.get("id"))
            if cid > max_id:
                max_id = cid
        except Exception:
            continue
        nm = str(c.get("name") or "")
        if nm and nm not in by_name:
            by_name[nm] = c

    assigned: list[tuple[int, str]] = []

    for name, url in targets:
        existing = by_name.get(name)
        if existing is None:
            max_id += 1
            c = new_character_stub(max_id, name)
            chars.append(c)
            by_name[name] = c
            cid = max_id
        else:
            cid = int(existing["id"])
            existing["arcs"] = append_unique_str(existing.get("arcs"), "エルバフ編")
            existing["category"] = "戦う者達"
            existing["group"] = "エルバフ"

        out_path = THUMB_DIR / f"{cid}.webp"
        download_to_webp_400(url, out_path, quality=80)
        assigned.append((cid, name))

    chars.sort(key=lambda x: int(x.get("id", 0)) if isinstance(x, dict) else 0)
    CHAR_PATH.write_text(json.dumps(chars, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    print("追加/更新 完了:")
    for cid, name in assigned:
        print(f"  - {cid}: {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

