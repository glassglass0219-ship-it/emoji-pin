#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
import unicodedata
from pathlib import Path
from typing import Any, Iterable


def norm_name(s: str) -> str:
    # NFKC で互換文字/全半角を揃え、空白類と中点だけ落として比較キーにする
    t = unicodedata.normalize("NFKC", (s or "").strip())
    for ch in [" ", "　", "・", "\t", "\n", "\r"]:
        t = t.replace(ch, "")
    return t


def load_json(path: Path) -> Any:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def iter_extracted_rows(data: Any) -> Iterable[dict]:
    if isinstance(data, list):
        for row in data:
            if isinstance(row, dict):
                yield row
        return
    if isinstance(data, dict):
        # よくあるキーを試す
        for k in ["characters", "items", "data", "results", "rows"]:
            v = data.get(k)
            if isinstance(v, list):
                for row in v:
                    if isinstance(row, dict):
                        yield row
                return
    raise ValueError("抽出JSONの形式が不明です（配列 or dict{characters:[...] } を想定）")


def pick_name(row: dict) -> str:
    for k in ["name", "characterName", "jpName", "title"]:
        v = row.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def pick_image_url(row: dict) -> str:
    for k in ["imageUrl", "image_url", "image", "url", "faceUrl", "thumbnailUrl"]:
        v = row.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--input",
        default="onepiece_characters_full.json",
        help="抽出JSONパス（default: onepiece_characters_full.json）",
    )
    ap.add_argument(
        "--master",
        default="src/data/characters.json",
        help="マスターJSONパス（default: src/data/characters.json）",
    )
    ap.add_argument(
        "--output",
        default="review_list.csv",
        help="出力CSV名（default: review_list.csv）",
    )
    args = ap.parse_args()

    in_path = Path(args.input)
    master_path = Path(args.master)
    out_path = Path(args.output)

    if not in_path.exists():
        print(f"[ERROR] input not found: {in_path}", file=sys.stderr)
        return 2
    if not master_path.exists():
        print(f"[ERROR] master not found: {master_path}", file=sys.stderr)
        return 2

    extracted_raw = load_json(in_path)
    master_raw = load_json(master_path)
    if not isinstance(master_raw, list):
        raise ValueError("src/data/characters.json は配列である必要があります")

    master_names: list[str] = []
    for c in master_raw:
        if not isinstance(c, dict):
            continue
        n = c.get("name")
        if isinstance(n, str) and n.strip():
            master_names.append(n.strip())

    master_key_to_names: dict[str, list[str]] = {}
    for n in master_names:
        k = norm_name(n)
        master_key_to_names.setdefault(k, []).append(n)

    master_keys = list(master_key_to_names.keys())

    rows_out: list[list[str]] = []
    seen_extracted_keys: set[str] = set()

    for row in iter_extracted_rows(extracted_raw):
        name = pick_name(row)
        if not name:
            continue
        image_url = pick_image_url(row)
        k = norm_name(name)
        if not k:
            continue

        # 抽出側の重複は 1 行にまとめる（最初の1件だけ）
        if k in seen_extracted_keys:
            continue
        seen_extracted_keys.add(k)

        if k in master_key_to_names:
            decision = "既存一致"
            similar = " | ".join(master_key_to_names[k])
        else:
            # ★重複の疑い: 片方が片方に含まれる（正規化キーで判定）
            sims: list[str] = []
            for mk in master_keys:
                if not mk:
                    continue
                if k in mk or mk in k:
                    sims.extend(master_key_to_names.get(mk, []))
            if sims:
                decision = "★重複の疑い"
                # 同じ名前が複数キーから出た場合に備えて unique
                similar = " | ".join(dict.fromkeys(sims))
            else:
                decision = "＋新規候補"
                similar = ""

        rows_out.append([decision, name, similar, image_url])

    # utf-8-sig で出力
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["判定", "抽出名", "マスター内の類似名", "画像URL"])
        w.writerows(rows_out)

    print(f"Wrote {out_path} ({len(rows_out)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

