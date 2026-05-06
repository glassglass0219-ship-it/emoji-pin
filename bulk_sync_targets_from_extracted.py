#!/usr/bin/env python3
"""
指定した対象キャラ名リストについて、src/data/extracted/*.json を走査して
characters.json に追加・更新し、見つかった url から thumbnails を作成する。
"""

from __future__ import annotations

import argparse
import io
import json
import re
import unicodedata
from pathlib import Path
from typing import Any

import requests
from PIL import Image


ROOT = Path(__file__).resolve().parent
CHAR_PATH = ROOT / "src" / "data" / "characters.json"
EXTRACT_DIR = ROOT / "src" / "data" / "extracted"
THUMB_DIR = ROOT / "public" / "images" / "thumbnails"


FILE_TO_ARC: dict[str, str] = {
    "eastblue_wt100_faces.json": "東の海（イーストブルー）編",
    "alabasta_wt100_faces.json": "アラバスタ編",
    "sora_wt100_faces.json": "空島編",
    "davybackfight_wt100_faces.json": "デービーバックファイト編",
    "waterseven_wt100_faces.json": "ウォーターセブン編",
    "enieslobby_wt100_faces.json": "エニエス・ロビー編",
    "thriller Bark_wt100_faces.json": "スリラーバーク編",
    "sabaody_wt100_faces.json": "シャボンディ諸島編",
    "amazonlily_wt100_faces.json": "女ヶ島アマゾン・リリー編",
    "impeldown_wt100_faces.json": "大監獄インペルダウン編",
    "marineford_wt100_faces.json": "マリンフォード頂上戦争編",
    "fishmanisland_wt100_faces.json": "魚人島編",
    "punkhazard_wt100_faces.json": "パンクハザード編",
    "dressrosa_wt100_faces.json": "ドレスローザ編",
    "zou_wt100_faces.json": "ゾウ編",
    "whole cake_wt100_faces.json": "ホールケーキアイランド編",
    "Reverie_wt100_faces.json": "世界会議（レヴェリー）編",
    "wano_wt100_faces.json": "ワノ国編",
    "egghead_wt100_faces.json": "エッグヘッド編",
    "elbaph_wt100_faces.json": "エルバフ編",
    "godvalley_wt100_faces.json": "ゴッドバレー編",
    "hyoushi_wt100_faces.json": "表紙連載",
    "sonota_wt100_faces.json": "その他",
}


TARGET_NAMES: list[str] = [
    "スノウクイーン",
    "ハイパー雪だるさん",
    "ハサミ",
    "金魚姫",
    "海イノシシ",
    "ハチマキナマズ村の長老",
    "Dr.クロツル",
    "キュージ",
    "コーダ",
    "土番長",
    "森番長",
    "クラウ・D・クローバー",
    "スぺーシー中尉",
    "アタッチ",
    "コスモ軍曹",
    "ギャラクシー軍",
    "キャプテン・シーマーズ",
    "ツキミ博士",
    "ロズワード・シャルリア宮",
    "キャンディー",
    "マスケレドモ・ゴアユー鳥",
    "ドンキホーテ・ミョスガルド聖",
    "ノースバード",
    "イースタンバード",
    "トンジル",
    "トンスファー",
    "ビミネ",
    "鉄筋のスムージ",
    "ガブル",
    "海イヌのおまわりさん/海獣保安官",
    "昇り龍（りゅーのすけ）",
    "ワーニー",
    "ねこざえもん",
    "ミルキー",
    "虎三郎",
    "セーザ",
    "イワトビ",
    "ウホリシア",
    "チチリシア",
    "原",
    "トマティート",
    "フリカ",
    "エッタラ・チャウンカイ",
    "マウストゥー・マウスヤン",
    "スーカレ・タイネン",
    "シコン・ケッタイ",
    "メザスゾワン・ピースオ",
    "ラクシテモ・テルスベハナイカ博士",
    "スーカレ・カレホスイ",
    "デモーニ・アイヨ",
    "BLACK（巨大パチンコ黒カブト擬人化）",
    "蜜蜂兵",
    "オラブ",
    "電語虫",
    "グロッキーザウルス",
]

# 抽出JSON側の表記とズレるケース（検索は右側、登録名は左のTARGET_NAMESのまま）
SOURCE_NAME_ALIASES: dict[str, str] = {
    "ギャラクシー軍": "ギャラクシー将軍",
}


def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "").strip())


_SPACE_RE = re.compile(r"[ \t\u3000]+")


def norm_name(s: str) -> str:
    t = nfkc(s)
    t = _SPACE_RE.sub("", t)
    t = t.replace("・", "")
    t = t.replace("･", "")
    t = t.lower()
    return t


_PAREN_FW = ("（", "）")
_PAREN_HW = ("(", ")")


def strip_paren_content(s: str) -> str:
    """Remove all (...) and （…） bracket groups (nested naively)."""
    t = nfkc(s)
    out: list[str] = []
    i = 0
    depth = 0
    while i < len(t):
        ch = t[i]
        if ch in _PAREN_HW[0] + _PAREN_FW[0]:
            depth += 1
            i += 1
            continue
        if ch in _PAREN_HW[1] + _PAREN_FW[1]:
            if depth > 0:
                depth -= 1
            i += 1
            continue
        if depth == 0:
            out.append(ch)
        i += 1
    t2 = "".join(out)
    t2 = _SPACE_RE.sub("", t2)
    t2 = t2.replace("・", "").replace("･", "")
    return t2.lower()


def split_target_variants(target: str) -> list[str]:
    """
    "/" は「別名の区切り」として扱うが、
    例: 海イヌのおまわりさん/海獣保安官 のように“1つの正式名”に "/" が含まれるケースがある。
    その場合は周囲に空白が無い限り分割しない。
    """
    t = target.strip()
    if "/" not in t:
        return [t]
    if " / " in t or t.startswith("/") or t.endswith("/"):
        parts = [p.strip() for p in t.split("/") if p.strip()]
        return parts if len(parts) > 1 else [t]
    # 空白なしの "/" は分割しない（1名扱い）
    return [t]


def extract_url(obj: dict[str, Any]) -> str | None:
    for k in ("url", "image", "imageUrl", "src", "face", "faceUrl"):
        v = obj.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def resolve_json_path(base: Path, filename: str) -> Path | None:
    p = base / filename
    if p.exists():
        return p
    p2 = base / f"{filename}.json"
    if p2.exists():
        return p2
    return None


def load_extract_list(path: Path) -> list[dict[str, Any]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return [x for x in raw if isinstance(x, dict)]
    raise ValueError(f"unexpected json root in {path}")


def append_arc_unique(char: dict[str, Any], arc: str) -> None:
    cur = char.get("arcs")
    if not isinstance(cur, list):
        cur = []
    seen = {str(x).strip() for x in cur if isinstance(x, str)}
    a = arc.strip()
    if a and a not in seen:
        cur.append(a)
    char["arcs"] = cur


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
        "abilities": [],
        "coAppearances": [],
        "alias": "",
        "en_name": "",
        "arcs": [],
        "category": "",
        "group": "",
    }


def download_to_webp_400(url: str, out_path: Path, quality: int = 80) -> None:
    if url.startswith("http://") or url.startswith("https://"):
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        data = r.content
    else:
        p = Path(url)
        if not p.is_absolute():
            p = (ROOT / p).resolve()
        data = p.read_bytes()

    img = Image.open(io.BytesIO(data)).convert("RGBA")
    img = img.resize((400, 400), Image.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "WEBP", quality=quality, method=6)


def find_existing_by_name(chars: list[dict[str, Any]], name: str) -> dict[str, Any] | None:
    for c in chars:
        if isinstance(c, dict) and str(c.get("name") or "") == name:
            return c
    return None


def target_matches_source(target: str, src_name: str) -> bool:
    n_src = norm_name(src_name)
    n_src_np = strip_paren_content(src_name)
    for v in split_target_variants(target):
        if v == src_name or nfkc(v) == nfkc(src_name):
            return True
        if norm_name(v) == n_src:
            return True
        if strip_paren_content(v) and strip_paren_content(v) == n_src_np:
            return True
        alias = SOURCE_NAME_ALIASES.get(v)
        if alias:
            if alias == src_name or nfkc(alias) == nfkc(src_name):
                return True
            if norm_name(alias) == n_src:
                return True
            if strip_paren_content(alias) and strip_paren_content(alias) == n_src_np:
                return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--overwrite-image", action="store_true", help="既存webpも上書きする")
    args = ap.parse_args()

    chars = json.loads(CHAR_PATH.read_text(encoding="utf-8"))
    if not isinstance(chars, list):
        raise SystemExit("characters.json must be a list")

    max_id = 0
    for c in chars:
        if isinstance(c, dict):
            try:
                max_id = max(max_id, int(c.get("id")))
            except Exception:
                pass

    matches: dict[str, list[tuple[str, str, str]]] = {t: [] for t in TARGET_NAMES}

    for fn, arc in FILE_TO_ARC.items():
        p = resolve_json_path(EXTRACT_DIR, fn)
        if p is None:
            print(f"[warn] missing extract file: {fn}")
            continue
        rows = load_extract_list(p)

        for row in rows:
            src_name = str(row.get("name") or "")
            if not src_name:
                continue
            url = extract_url(row)
            if not url:
                continue

            for target in TARGET_NAMES:
                if target_matches_source(target, src_name):
                    matches[target].append((p.name, arc, url))

    not_found: list[str] = []
    new_count = 0
    updated_count = 0

    for target in TARGET_NAMES:
        hits = matches.get(target) or []
        if not hits:
            not_found.append(target)
            continue

        existed = find_existing_by_name(chars, target) is not None
        ch = find_existing_by_name(chars, target)
        if ch is None:
            max_id += 1
            ch = new_character_stub(max_id, target)
            chars.append(ch)
            new_count += 1
        else:
            updated_count += 1

        for _fn, arc, _url in hits:
            append_arc_unique(ch, arc)

        _fn0, _arc0, url0 = hits[0]
        out = THUMB_DIR / f"{int(ch['id'])}.webp"
        if args.dry_run:
            print(f"[dry-run] {target} id={ch['id']} arc_hits={len(hits)} image={url0} -> {out}")
            continue

        if out.exists() and not args.overwrite_image:
            print(f"[skip-image] exists {out} (use --overwrite-image)")
        else:
            try:
                download_to_webp_400(url0, out, quality=80)
            except Exception as e:
                print(f"[image-fail] {target} id={ch['id']} url={url0} err={e}")

    if not args.dry_run:
        chars.sort(key=lambda x: int(x.get("id", 0)) if isinstance(x, dict) else 0)
        CHAR_PATH.write_text(json.dumps(chars, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    print(f"\nnew_characters={new_count} updated_or_touched={updated_count}")
    print("\n=== Not found in extracted JSON (after full scan) ===")
    for x in not_found:
        print(x)
    print(f"\nnot_found_count={len(not_found)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
