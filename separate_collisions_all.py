#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import time
from pathlib import Path
from typing import Any

import requests
from PIL import Image

import sync_images as si
import sync_images_v3 as v3


def nfkc(s: str) -> str:
    return v3.nfkc(s)


def read_collision_report(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader(f)
        return list(r)


def split_names(s: str) -> list[str]:
    return [x.strip() for x in (s or "").split(" / ") if x.strip()]


def load_faces_any(path: Path) -> list[dict[str, Any]]:
    # allow .json.json fallback via v3 helper
    p = v3.resolve_source_path(path)
    return v3.load_faces_json(p)


def download_to_webp(session: requests.Session, url: str, out_path: Path) -> None:
    resp = session.get(url, timeout=90)
    resp.raise_for_status()
    im = Image.open(io.BytesIO(resp.content))
    im = im.convert("RGBA")
    im = im.resize((400, 400), Image.Resampling.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    im.save(out_path, format="WEBP", quality=80, method=6)


def new_character_stub(cid: int, name: str) -> dict[str, Any]:
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


def find_char_exact(chars: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    t = nfkc(name)
    for c in chars:
        if not isinstance(c, dict):
            continue
        if nfkc(str(c.get("name") or "")) == t:
            return c
    return None


def max_id(chars: list[dict[str, Any]]) -> int:
    m = 0
    for c in chars:
        if not isinstance(c, dict):
            continue
        try:
            m = max(m, int(c.get("id") or 0))
        except Exception:
            pass
    return m


def arc_name_from_filename(fname: str) -> str:
    """
    extractedのファイル名 -> arcs用の日本語ラベル（プロジェクトで使っている表記）
    """
    n = fname.lower().replace(" ", "")
    if "eastblue" in n:
        return "東の海（イーストブルー）編"
    if "alabasta" in n:
        return "アラバスタ編"
    if "sora" in n:
        return "空島編"
    if "davybackfight" in n:
        return "デービーバックファイト編"
    if "waterseven" in n:
        return "ウォーターセブン編"
    if "enieslobby" in n:
        return "エニエス・ロビー編"
    if "thrillerbark" in n:
        return "スリラーバーク編"
    if "sabaody" in n:
        return "シャボンディ諸島編"
    if "amazonlily" in n:
        return "アマゾン・リリー編"
    if "impeldown" in n:
        return "インペルダウン編"
    if "marineford" in n:
        return "マリンフォード頂上戦争編"
    if "fishmanisland" in n:
        return "魚人島編"
    if "punkhazard" in n:
        return "パンクハザード編"
    if "dressrosa" in n:
        return "ドレスローザ編"
    if "zou" in n:
        return "ゾウ編"
    if "wholecake" in n or "whole_cake" in n or "wholecake" in n:
        return "ホールケーキアイランド編"
    if "reverie" in n:
        return "レヴェリー編"
    if "wano" in n:
        return "ワノ国編"
    if "egghead" in n:
        return "エッグヘッド編"
    if "elbaph" in n:
        return "エルバフ編"
    if "godvalley" in n:
        return "ゴッドバレー編"
    if "hyoushi" in n:
        return "表紙連載"
    if "sonota" in n:
        return "その他"
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(description="comprehensive_collision_report.csv を全て別キャラとして分離し、画像も新IDで保存")
    ap.add_argument("--report", default="comprehensive_collision_report.csv")
    ap.add_argument("--extracted-dir", default="src/data/extracted")
    ap.add_argument("--characters", default="src/data/characters.json")
    ap.add_argument("--sleep", type=float, default=0.22)
    args = ap.parse_args()

    os.chdir(si.ROOT)

    report_path = Path(args.report)
    extracted_dir = Path(args.extracted_dir)
    chars_path = Path(args.characters)

    rows = read_collision_report(report_path)
    chars: list[dict[str, Any]] = json.loads(chars_path.read_text(encoding="utf-8"))
    si.ensure_arcs_field(chars)

    # build name->url map per file
    file_to_name_url: dict[str, dict[str, str]] = {}
    for p in extracted_dir.glob("*.json*"):
        try:
            faces = load_faces_any(p)
        except Exception:
            continue
        mp: dict[str, str] = {}
        for r in faces:
            nm = str(r.get("name") or "").strip()
            url = str(r.get("url") or "").strip()
            if nm and url:
                mp[nfkc(nm)] = url
        file_to_name_url[p.name] = mp

    session = requests.Session()
    session.headers.update({"User-Agent": si.CHROME_UA})

    cur_max = max_id(chars)
    created = 0
    reused = 0
    downloaded_ok = 0
    downloaded_fail = 0

    # process only (ALL) rows to avoid duplicating per-file entries
    for r in rows:
        if r.get("ファイル名") != "(ALL)":
            continue
        master_id = int(r["マスターID"])
        master_name = r.get("マスター名", "").strip()
        names = split_names(r.get("ソース側で見つかった名前のリスト", ""))
        if len(names) <= 1:
            continue

        master = next((c for c in chars if isinstance(c, dict) and int(c.get("id", -1)) == master_id), None)
        if isinstance(master, dict):
            si.append_arc_unique(master, arc_name_from_filename("egghead_wt100_faces.json"))  # no-op if empty

        for nm in names:
            if nfkc(nm) == nfkc(master_name) and find_char_exact(chars, master_name) is not None:
                # keep as master
                continue

            existing = find_char_exact(chars, nm)
            if existing is not None:
                reused += 1
                # attach arc(s) if we can find from any file that contains this name
                for fname, mp in file_to_name_url.items():
                    if nfkc(nm) in mp:
                        arc = arc_name_from_filename(fname)
                        if arc:
                            si.append_arc_unique(existing, arc)
                continue

            cur_max += 1
            new_id = cur_max
            new_char = new_character_stub(new_id, nm)

            # attach arcs based on files that contain this name
            arcs_added = 0
            for fname, mp in file_to_name_url.items():
                if nfkc(nm) in mp:
                    arc = arc_name_from_filename(fname)
                    if arc:
                        si.append_arc_unique(new_char, arc)
                        arcs_added += 1
            chars.append(new_char)
            created += 1

            # image: pick first matching file
            picked_url = None
            for fname, mp in file_to_name_url.items():
                u = mp.get(nfkc(nm))
                if u:
                    picked_url = u
                    break
            if picked_url:
                out_p = si.PUBLIC_THUMB / f"{new_id}.webp"
                if not out_p.exists():
                    try:
                        download_to_webp(session, picked_url, out_p)
                        downloaded_ok += 1
                    except Exception:
                        downloaded_fail += 1
                time.sleep(max(0.0, args.sleep))

    chars.sort(key=lambda x: int(str(x.get("id", 0)) or 0) if isinstance(x, dict) else 0)
    chars_path.write_text(json.dumps(chars, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    print(f"created_new_chars: {created}")
    print(f"reused_existing_exact_name: {reused}")
    print(f"image_download_ok: {downloaded_ok}")
    print(f"image_download_fail: {downloaded_fail}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

