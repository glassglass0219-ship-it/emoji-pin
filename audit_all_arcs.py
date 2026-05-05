#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import sync_images as si
import sync_images_v3 as v3


def uniq_preserve(xs: Iterable[str]) -> list[str]:
    out: list[str] = []
    seen = set()
    for x in xs:
        k = v3.nfkc(x)
        if not k or k in seen:
            continue
        seen.add(k)
        out.append(x)
    return out


TITLE_PREFIXES = [
    "赤髪の",
    "麦わらの",
    "〝",
    "“",
    "『",
    "「",
]


def strip_title_like_prefix(s: str) -> str:
    t = v3.nfkc(s)
    for p in TITLE_PREFIXES:
        if t.startswith(p):
            return t[len(p) :].strip(" 」』〟”")
    return t


def canonical_variation_key(name: str) -> str:
    """
    「表記ゆれ」判定のための簡易キー。
    - NFKC
    - 括弧除去
    - 記号除去（・/空白/!/?）
    - タイトルっぽい接頭辞除去（完全ではない）
    """
    t = strip_title_like_prefix(name)
    return v3.norm_name(t)


STRICT_VARIANT_HINT_RE = re.compile(
    r"(PUNK0[1-6]|PUNK[ ]?0[1-6]|サテライト|マーク|POLICE|S-|セラフィム|パシフィスタ)",
    re.IGNORECASE,
)


def is_obviously_distinct_variant(names: list[str]) -> bool:
    """
    要分離寄りの判定（ドメイン知識を完全に入れるのは難しいので、
    明らかに「モデル/個体/派生」を示す記号が含まれる場合を強く要分離扱い）。
    """
    for n in names:
        if STRICT_VARIANT_HINT_RE.search(v3.nfkc(n)):
            return True
    return False


def classify_collision(master_name: str, source_names: list[str]) -> str:
    """
    判定:
    - 許容（表記ゆれ）: すべての名前が同一variation_key、または相互に包含（短い方>=3）
    - 要分離（別キャラ）: それ以外、または variant ヒントがある
    """
    if len(source_names) <= 1:
        return "許容（表記ゆれ）"

    if is_obviously_distinct_variant([master_name] + source_names):
        return "要分離（別キャラ）"

    keys = [canonical_variation_key(x) for x in ([master_name] + source_names)]
    keys = [k for k in keys if k]
    if keys and all(k == keys[0] for k in keys):
        return "許容（表記ゆれ）"

    # containment check among normalized forms
    norms = [canonical_variation_key(x) for x in ([master_name] + source_names)]
    norms = [n for n in norms if n]
    if norms:
        base = norms[0]
        ok = True
        for n in norms[1:]:
            shorter, longer = (base, n) if len(base) <= len(n) else (n, base)
            if len(shorter) >= 3 and shorter in longer:
                continue
            shorter2, longer2 = (n, base) if len(n) <= len(base) else (base, n)
            if len(shorter2) >= 3 and shorter2 in longer2:
                continue
            ok = False
            break
        if ok:
            return "許容（表記ゆれ）"

    return "要分離（別キャラ）"


def resolve_extracted_file(extracted_dir: Path, base_name: str) -> Path:
    """
    指定リストのファイル名に対し、.json.json を含む実体を探す。
    """
    p = extracted_dir / base_name
    if p.exists():
        return p
    # よくある二重拡張子
    p2 = extracted_dir / f"{base_name}.json"
    if p2.exists():
        return p2
    raise FileNotFoundError(str(p))


def main() -> int:
    ap = argparse.ArgumentParser(description="extracted全アークの名寄せ衝突を横断監査")
    ap.add_argument("--extracted-dir", default="src/data/extracted")
    ap.add_argument("--characters", default="src/data/characters.json")
    ap.add_argument("--output", default="comprehensive_collision_report.csv")
    args = ap.parse_args()

    extracted_dir = Path(args.extracted_dir)
    chars_path = Path(args.characters)
    out_path = Path(args.output)

    # 指定23ファイル（ユーザー提示）
    base_files = [
        "eastblue_wt100_faces.json",
        "alabasta_wt100_faces.json",
        "sora_wt100_faces.json",
        "davybackfight_wt100_faces.json",
        "waterseven_wt100_faces.json",
        "enieslobby_wt100_faces.json",
        "thiller Bark_wt100_faces.json",
        "sabaody_wt100_faces.json",
        "amazonlily_wt100_faces.json",
        "impeldown_wt100_faces.json",
        "marineford_wt100_faces.json",
        "fishmanisland_wt100_faces.json",
        "punkhazard_wt100_faces.json",
        "dressrosa_wt100_faces.json",
        "zou_wt100_faces.json",
        "whole cake_wt100_faces.json",
        "Reverie_wt100_faces.json",
        "wano_wt100_faces.json",
        "egghead_wt100_faces.json",
        "elbaph_wt100_faces.json",
        "godvalley_wt100_faces.json",
        "hyoushi_wt100_faces.json",
        "sonota_wt100_faces.json",
    ]

    chars: list[dict[str, Any]] = json.loads(chars_path.read_text(encoding="utf-8"))
    si.ensure_arcs_field(chars)
    renames = si.load_renames(si.CORRECTIONS_PATH)
    merges = v3.load_merges(si.CORRECTIONS_PATH)

    # master_id -> master_name
    master_name_by_id: dict[int, str] = {}
    for c in chars:
        if not isinstance(c, dict):
            continue
        try:
            cid = int(c.get("id"))
        except Exception:
            continue
        master_name_by_id[cid] = str(c.get("name") or "")

    # master_id -> file -> [source names]
    hits: dict[int, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

    for base in base_files:
        try:
            fp = resolve_extracted_file(extracted_dir, base)
        except FileNotFoundError:
            # ある程度ゆるく探す（大小文字/スペース違い）
            # extracted内の全ファイルから、baseの先頭（_wt100_faces.json）を含むものを拾う
            stem = base.replace("_wt100_faces.json", "").lower().replace(" ", "")
            candidates = sorted(extracted_dir.glob("*.json*"))
            found = None
            for c in candidates:
                s = c.name.lower().replace(" ", "")
                if stem and stem in s and "wt100" in s and "faces" in s:
                    found = c
                    break
            if found is None:
                print(f"[WARN] not found: {base}")
                continue
            fp = found

        faces = v3.load_faces_json(fp)
        for row in faces:
            src_name = str(row.get("name") or "").strip()
            resolved = v3.resolve_merge_display(src_name, merges)
            # v3と同じ: strictは exactのみ。それ以外はsi.find_character→v3 fuzzy
            if v3.is_strict_variant_name(resolved):
                ch = v3.find_exact_name(chars, resolved)
            else:
                ch = si.find_character(chars, resolved, "", renames)
                if ch is None:
                    m = v3.best_match_for_name(chars, resolved, renames)
                    if m is not None:
                        ch = m.char
            if ch is None:
                continue
            cid = int(ch.get("id"))
            hits[cid][fp.name].append(src_name)

    # collisions: master_id with 2+ distinct source names overall (after NFKC uniq)
    rows_out: list[dict[str, Any]] = []
    for cid, file_map in sorted(hits.items(), key=lambda x: x[0]):
        # flatten distinct names across files
        all_names = []
        for ns in file_map.values():
            all_names.extend(ns)
        all_names = uniq_preserve(all_names)
        if len(all_names) <= 1:
            continue

        master_name = master_name_by_id.get(cid, "")
        # per file row (so user can see where)
        for fname, ns in sorted(file_map.items(), key=lambda x: x[0]):
            ns_u = uniq_preserve(ns)
            if len(ns_u) <= 1:
                continue
            verdict = classify_collision(master_name, ns_u)
            rows_out.append(
                {
                    "マスターID": cid,
                    "マスター名": master_name,
                    "ソース側で見つかった名前のリスト": " / ".join(ns_u),
                    "ファイル名": fname,
                    "判定": verdict,
                }
            )

        # also add an aggregated row if collision spans multiple files but each file individually had 1
        multi_files = [k for k, v in file_map.items() if uniq_preserve(v)]
        if len(multi_files) >= 2:
            verdict_all = classify_collision(master_name, all_names)
            rows_out.append(
                {
                    "マスターID": cid,
                    "マスター名": master_name,
                    "ソース側で見つかった名前のリスト": " / ".join(all_names),
                    "ファイル名": "(ALL)",
                    "判定": verdict_all,
                }
            )

    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["マスターID", "マスター名", "ソース側で見つかった名前のリスト", "ファイル名", "判定"])
        for r in rows_out:
            w.writerow([r["マスターID"], r["マスター名"], r["ソース側で見つかった名前のリスト"], r["ファイル名"], r["判定"]])

    need_sep = sum(1 for r in rows_out if r["判定"] == "要分離（別キャラ）")
    print(f"Wrote {out_path} rows={len(rows_out)} need_separate={need_sep}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

