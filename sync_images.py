#!/usr/bin/env python3
"""
WT100 顔画像を取得し public/images/thumbnails/{id}.webp に保存。
characters.json / name_corrections.json と照合して既存キャラへ紐付け、無ければ新規追加。
名前はユーザ指定オーバーライド + 公式サイト midterm（JA/EN）の img alt をマージ。
face 0001〜0122 のうち名前が解決できた分のみ処理（公式 midterm に無い番号は src/data/wt100_faces_manifest.json へ追記マージで拡張可能）。
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import time
import unicodedata
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "src" / "data"
PUBLIC_THUMB = ROOT / "public" / "images" / "thumbnails"

CHAR_PATH = DATA / "characters.json"
CORRECTIONS_PATH = DATA / "name_corrections.json"
# 公式自動マージ結果を毎回上書き保存。手動で face を足す場合は OVERRIDES を編集。
MANIFEST_PATH = DATA / "wt100_faces_manifest.json"
OVERRIDES_PATH = DATA / "wt100_faces_overrides.json"

JA_MIDTERM = "https://onepiecewt100-2026.com/ja/midterm-rankings/"
EN_MIDTERM = "https://onepiecewt100-2026.com/en/midterm-rankings/"

BASE_URL = "https://onepiecewt100-2026.com/assets/faces/{fid}.png?v=gjdgxu"

CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

FACE_RANGE = range(1, 123)

WT100_USER_OVERRIDES: dict[str, str] = {
    "0001": "モンキー・Ｄ・ルフィ",
    "0002": "ロロノア・ゾロ",
    "0003": "ナミ",
    "0004": "ウソップ",
    "0005": "サンジ",
    "0011": "ゴーイング・メリー号",
    "0014": "ゴール・Ｄ・ロジャー",
    "0015": "アンジョウ",
    "0016": "モンスター",
    "0017": "シャンクス",
    "0018": "ラッキー・ルウ",
    "0019": "ヤソップ",
    "0020": "ベン・ベックマン",
    "0021": "MIKIO ITOO",
    "0022": "マキノ",
    "0023": "ヒグマ",
    "0024": "ギョルさん",
    "0025": "チキンおばさん",
    "0026": "ウープ・スラップ",
    "0027": "近海の主（ゴア王国）",
    "0028": "コビー",
    "0029": "アルビダ",
    "0030": "ヘッポコ",
    "0031": "ペッポコ",
    "0032": "ポッポコ",
    "0033": "リカ",
    "0034": "ヘルメッポ",
    "0035": "ソーロ",
    "0036": "リリカ",
    "0037": "モーガン",
    "0038": "ロッカク",
    "0039": "ウッカリー",
    "0040": "くいな",
    "0041": "コウシロウ",
    "0042": "リッパー",
    "0043": "怪鳥ピンキー",
    "0044": "綱渡りフナンボローズ",
    "0045": "怪力ドミンゴス",
    "0046": "バギー",
    "0047": "どーも君",
    "0048": "軽業フワーズ",
    "0049": "モージ",
    "0050": "リッチー",
    "0051": "シュシュ",
    "0052": "ブードル",
    "0053": "ホッカー",
    "0054": "ポロ",
    "0055": "カバジ",
    "0056": "ココックス",
    "0057": "ガイモン",
    "0058": "モーニン",
    "0059": "にんじん",
    "0060": "ピーマン",
    "0061": "たまねぎ",
    "0062": "クロ（クラハドール）",
    "0063": "カヤ",
    "0064": "門番",
    "0065": "メリー",
}


def normalize_key(name: str) -> str:
    s = unicodedata.normalize("NFKC", (name or "").strip())
    return re.sub(r"[・\s\-★]", "", s)


def normalize_en_compact(name: str) -> str:
    s = unicodedata.normalize("NFKC", (name or "").strip())
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def strip_qualifiers(name: str) -> str:
    s = unicodedata.normalize("NFKC", name or "")
    s = re.sub(r"（[^）]*）", "", s)
    s = re.sub(r"\([^)]*\)", "", s)
    return s.strip()


def scrape_midterm_alt_map(url: str) -> dict[str, str]:
    r = requests.get(url, headers={"User-Agent": CHROME_UA}, timeout=90)
    r.raise_for_status()
    pairs = re.findall(
        r'src="/assets/faces/(\d+)\.png[^"]*"[^>]*alt="([^"]+)"',
        r.text,
    )
    return {a: unicodedata.normalize("NFKC", b) for a, b in pairs}


def load_renames(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    mp = data.get("renames") or {}
    return {normalize_key(k): str(v) for k, v in mp.items() if isinstance(k, str)}


def apply_rename(norm_key_val: str, renames_norm_to_canon: dict[str, str]) -> str:
    return renames_norm_to_canon.get(norm_key_val, norm_key_val)


def collect_candidate_strings(char: dict) -> list[str]:
    out: list[str] = []
    for key in ("name", "reading", "alias"):
        v = char.get(key)
        if not isinstance(v, str):
            continue
        v = v.strip()
        if not v:
            continue
        out.append(v)
        if key == "alias":
            for part in re.split(r"[,、／/]", v):
                p = part.strip()
                if p:
                    out.append(p)
    en = char.get("en_name")
    if isinstance(en, str) and en.strip():
        out.append(en.strip())
    return list(dict.fromkeys(out))


def score_name_match(wt_norm: str, cand_norm: str) -> int:
    if not wt_norm or not cand_norm:
        return 0
    if wt_norm == cand_norm:
        return 1000 + len(cand_norm)
    shorter, longer = (wt_norm, cand_norm) if len(wt_norm) <= len(cand_norm) else (cand_norm, wt_norm)
    if len(shorter) >= 4 and shorter in longer:
        return 500 + len(shorter)
    return 0


def find_character(
    chars: list[dict],
    name_ja: str,
    name_en: str,
    renames_norm_to_canon: dict[str, str],
) -> dict | None:
    wt_ja_terms: list[str] = []
    if name_ja:
        sj = strip_qualifiers(name_ja)
        nk = normalize_key(sj)
        wt_ja_terms.extend([sj, nk, apply_rename(nk, renames_norm_to_canon)])

    wt_en_term = name_en.strip() if name_en else ""

    best: tuple[int, dict] | None = None
    for ch in chars:
        if not isinstance(ch, dict):
            continue
        best_local = 0

        en_db = str(ch.get("en_name") or "").strip()
        if wt_en_term and en_db:
            enc = normalize_en_compact(en_db)
            wte = normalize_en_compact(wt_en_term)
            if enc and wte and (enc == wte or (len(wte) >= 4 and wte in enc)):
                best_local = max(best_local, 800 + min(len(enc), len(wte)))

        if wt_en_term and not name_ja:
            # JA 無し・英語のみ（例: MIKIO ITOO）
            for cand in collect_candidate_strings(ch):
                if re.search(r"[ぁ-んァ-ン一-龥]", cand):
                    continue
                wte = normalize_en_compact(wt_en_term)
                cce = normalize_en_compact(cand)
                if wte and cce and (cce == wte or (len(wte) >= 4 and wte in cce)):
                    best_local = max(best_local, 750)

        for wt in wt_ja_terms:
            if not wt:
                continue
            wtn = normalize_key(strip_qualifiers(wt))
            if len(wtn) < 2:
                continue
            for cand in collect_candidate_strings(ch):
                cn = normalize_key(strip_qualifiers(cand))
                cn2 = apply_rename(cn, renames_norm_to_canon)
                best_local = max(best_local, score_name_match(wtn, cn), score_name_match(wtn, cn2))

        if best_local > 0 and (best is None or best_local > best[0]):
            best = (best_local, ch)

    return best[1] if best else None


def remove_stale_images(char_id: int) -> None:
    for ext in (".png", ".jpg", ".jpeg"):
        p = PUBLIC_THUMB / f"{char_id}{ext}"
        if p.exists():
            p.unlink()


def download_to_webp(session: requests.Session, url: str, out_path: Path) -> None:
    r = session.get(url, timeout=90)
    r.raise_for_status()
    im = Image.open(io.BytesIO(r.content))
    im = im.convert("RGBA")
    im = im.resize((400, 400), Image.Resampling.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    im.save(out_path, format="WEBP", quality=82, method=6)


def load_face_overrides(path: Path) -> dict[str, dict]:
    """face_id -> {name_ja?, name_en?, url?}"""
    if not path.exists():
        return {}
    try:
        with path.open(encoding="utf-8") as f:
            raw = json.load(f)
    except json.JSONDecodeError:
        return {}
    out: dict[str, dict] = {}
    if isinstance(raw, list):
        for row in raw:
            if not isinstance(row, dict):
                continue
            fid = str(row.get("face_id") or "").zfill(4)
            if len(fid) != 4:
                continue
            out[fid] = row
    return out


def build_row(
    fid: str,
    ja_map: dict[str, str],
    en_map: dict[str, str],
    extra: dict[str, dict],
) -> dict | None:
    ex = extra.get(fid) or {}
    url = str(ex.get("url") or "").strip() or BASE_URL.format(fid=fid)
    ja = str(ex.get("name_ja") or "").strip()
    en = str(ex.get("name_en") or "").strip()
    if not ja:
        ja = WT100_USER_OVERRIDES.get(fid) or ja_map.get(fid) or ""
    if not en:
        en = en_map.get(fid) or ""
    if not ja and not en:
        return None
    return {"face_id": fid, "url": url, "name_ja": ja, "name_en": en}


def append_arc_unique(char: dict, arc_name: str) -> None:
    """キャラの arcs に編名を追加（重複しない）。"""
    arc_name = (arc_name or "").strip()
    if not arc_name:
        return
    arcs = char.setdefault("arcs", [])
    if arc_name not in arcs:
        arcs.append(arc_name)


def ensure_arcs_field(chars: list[dict]) -> None:
    for c in chars:
        if isinstance(c, dict):
            c.setdefault("arcs", [])


def new_character_stub(cid: int, name: str, en_hint: str) -> dict:
    return {
        "id": cid,
        "name": name,
        "reading": "",
        "gender": "",
        "affiliation": "",
        "devilFruit": "",
        "bounty": "",
        "birthday": "",
        "firstAppearance": "",
        "appearances": [],
        "covers": [],
        "abilities": [],
        "coAppearances": [],
        "alias": "",
        "en_name": en_hint or "",
        "arcs": [],
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="WT100 顔画像同期・編（アーク）タグ付け")
    p.add_argument(
        "--arc-name",
        default="",
        help='例: 「東の海（イーストブルー）編」。指定時、処理したキャラの arcs に追加（重複なし）。',
    )
    p.add_argument(
        "--skip-download",
        action="store_true",
        help="画像ダウンロード・WebP変換を行わず、マニフェスト生成・編タグのみ（マッチしない face はスキップ）。",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    os.chdir(ROOT)
    arc_name = (args.arc_name or "").strip()

    renames_norm_to_canon = load_renames(CORRECTIONS_PATH)

    ja_alt = scrape_midterm_alt_map(JA_MIDTERM)
    time.sleep(0.35)
    en_alt = scrape_midterm_alt_map(EN_MIDTERM)
    ov = load_face_overrides(OVERRIDES_PATH)

    by_id: dict[str, dict] = {}
    for i in FACE_RANGE:
        fid = f"{i:04d}"
        row = build_row(fid, ja_alt, en_alt, ov)
        if row:
            by_id[fid] = row

    manifest = [by_id[k] for k in sorted(by_id.keys())]

    with MANIFEST_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"マニフェスト: {len(manifest)} 件（0001〜0122・ユーザオーバーライド・midterm を統合）")
    print(f"出力: {MANIFEST_PATH}")

    with CHAR_PATH.open(encoding="utf-8") as f:
        chars: list[dict] = json.load(f)

    ensure_arcs_field(chars)

    session = requests.Session()
    session.headers.update({"User-Agent": CHROME_UA})

    applied_existing = 0
    added_new = 0
    next_id = max(int(c["id"]) for c in chars if isinstance(c, dict) and str(c.get("id", "")).isdigit())

    for row in manifest:
        url = row["url"]
        ja = row.get("name_ja") or ""
        en = row.get("name_en") or ""

        display_name = ja or en
        ch = find_character(chars, ja, en, renames_norm_to_canon)

        if ch is None:
            if args.skip_download:
                print(f"[SKIP 未マッチ] face {row['face_id']} {display_name}")
                continue
            next_id += 1
            stub = new_character_stub(next_id, display_name, en if ja != display_name else "")
            chars.append(stub)
            ch = stub
            added_new += 1
            print(f"[NEW id={next_id}] {display_name} (face {row['face_id']})")
        else:
            applied_existing += 1

        if arc_name:
            append_arc_unique(ch, arc_name)

        if not args.skip_download:
            cid = int(ch["id"])
            remove_stale_images(cid)
            out_p = PUBLIC_THUMB / f"{cid}.webp"
            download_to_webp(session, url, out_p)
            time.sleep(0.25)

    chars.sort(key=lambda x: int(x.get("id", 0)))

    with CHAR_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print()
    if args.skip_download:
        print("（--skip-download）画像処理はスキップしました。")
    else:
        print(f"既存キャラへ画像適用: {applied_existing} 名")
        print(f"新規追加（名簿）: {added_new} 名")
        print(f"サムネ保存先: {PUBLIC_THUMB}")
    if arc_name:
        print(f"編タグ適用: 「{arc_name}」")


if __name__ == "__main__":
    main()
