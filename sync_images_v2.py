#!/usr/bin/env python3
"""
WT100 などから用意した [{name, url}] JSON と characters.json を同期する。
- name は name_corrections.json の renames / merges を適用して照合（sync_images と同様の find_character）
- 既存キャラ: public/images/thumbnails/{id}.webp が無いときのみ DL・400x400 WebP 変換
- 新規キャラ: max(id)+1 でスタブ作成後、同上で画像保存
- arcs に --arc-name を重複なく追加
"""

from __future__ import annotations

import argparse
import json
import os
import time
import unicodedata
from pathlib import Path

import requests

import sync_images as si

ROOT = si.ROOT
CHAR_PATH = si.CHAR_PATH
CORRECTIONS_PATH = si.CORRECTIONS_PATH
PUBLIC_THUMB = si.PUBLIC_THUMB


def load_merges(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    mp = data.get("merges") or {}
    out: dict[str, str] = {}
    for k, v in mp.items():
        if not isinstance(k, str) or not isinstance(v, str):
            continue
        nk = unicodedata.normalize("NFKC", k.strip())
        nv = unicodedata.normalize("NFKC", v.strip())
        if nk:
            out[nk] = nv
    return out


def resolve_merge_display(name: str, merges_exact: dict[str, str]) -> str:
    n = unicodedata.normalize("NFKC", (name or "").strip())
    return merges_exact.get(n, n)


def is_valid_face_png_url(url: str) -> bool:
    u = (url or "").strip().lower().split("?", 1)[0]
    return "/assets/faces/" in u and u.endswith(".png")


def load_faces_json(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        raw = json.load(f)
    if not isinstance(raw, list):
        raise ValueError("faces JSON は配列である必要があります")
    rows = []
    for i, row in enumerate(raw):
        if not isinstance(row, dict):
            continue
        nm = str(row.get("name") or "").strip()
        url = str(row.get("url") or "").strip()
        if not nm or not url:
            raise ValueError(f"行 {i}: name と url が必須です")
        if not is_valid_face_png_url(url):
            print(f"[SKIP 非顔PNG] 行 {i} {nm!r} … {url[:72]}")
            continue
        rows.append({"name": nm, "url": url})
    return rows


def max_char_id(chars: list[dict]) -> int:
    best = 0
    for c in chars:
        if not isinstance(c, dict):
            continue
        cid = c.get("id")
        if cid is None:
            continue
        s = str(cid).strip()
        if s.isdigit():
            best = max(best, int(s))
    return best


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="WT100 顔 JSON と characters.json / サムネを同期")
    p.add_argument(
        "--arc-name",
        required=True,
        help='例: 「アラバスタ編」。処理したキャラの arcs に追加（重複なし）',
    )
    p.add_argument(
        "--json-file",
        type=Path,
        default=ROOT / "src" / "data" / "arabasta_wt100_faces.json",
        help="[{name, url}, ...] 形式の JSON ファイルパス",
    )
    p.add_argument(
        "--sleep",
        type=float,
        default=0.22,
        help="ダウンロード間隔（秒）",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    os.chdir(ROOT)

    arc_name = (args.arc_name or "").strip()
    faces_path = args.json_file if args.json_file.is_absolute() else ROOT / args.json_file

    renames = si.load_renames(CORRECTIONS_PATH)
    merges = load_merges(CORRECTIONS_PATH)
    faces_data = load_faces_json(faces_path)

    with CHAR_PATH.open(encoding="utf-8") as f:
        chars: list[dict] = json.load(f)

    si.ensure_arcs_field(chars)

    session = requests.Session()
    session.headers.update({"User-Agent": si.CHROME_UA})

    next_id = max_char_id(chars)

    downloaded = 0
    skipped_thumb = 0
    new_names: list[str] = []

    for row in faces_data:
        display_name = row["name"]
        url = row["url"]
        resolved = resolve_merge_display(display_name, merges)

        ch = si.find_character(chars, resolved, "", renames)

        if ch is None:
            next_id += 1
            stub = si.new_character_stub(next_id, resolved, "")
            chars.append(stub)
            ch = stub
            new_names.append(resolved)
            print(f"[NEW id={next_id}] {resolved}")

        if arc_name:
            si.append_arc_unique(ch, arc_name)

        cid = int(ch["id"])
        out_p = PUBLIC_THUMB / f"{cid}.webp"
        if out_p.exists():
            skipped_thumb += 1
            continue

        si.remove_stale_images(cid)
        si.download_to_webp(session, url, out_p)
        downloaded += 1
        time.sleep(max(0.0, args.sleep))

    chars.sort(key=lambda x: int(str(x.get("id", 0))))

    with CHAR_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print()
    print(f"ソース: {faces_path} ({len(faces_data)} 件)")
    print(f"今回新しく画像をダウンロードした数: {downloaded}")
    print(f"既に画像があったためスキップした数: {skipped_thumb}")
    print(f"新しく名簿に追加されたキャラ数: {len(new_names)}")
    if new_names:
        print("新しく名簿に追加されたキャラ名:")
        for nm in new_names:
            print(f"  - {nm}")
    if arc_name:
        print(f"編タグ適用: 「{arc_name}」")


if __name__ == "__main__":
    main()
