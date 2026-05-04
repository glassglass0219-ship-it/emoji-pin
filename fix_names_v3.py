#!/usr/bin/env python3
"""キャラ正式名の一括更新（ID・appearances・covers は維持）。凶はロジャー海賊団のギンのみ対象。"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAR_PATH = ROOT / "src/data/characters.json"


def normalize(name: str) -> str:
    return re.sub(r"[・\s\-]", "", (name or "").strip())


RENAME_BY_NORM: dict[str, str] = {
    normalize("キビパイン"): "ミレ・パイン",
    normalize("アマズイ"): "ガンズイ",
    normalize("オオク"): "王直",
    normalize("マーロン"): "首領・マーロン",
    normalize("チョウ"): "お蝶",
}


def is_roger_crew_gin(c: dict) -> bool:
    """名前が「ギン」で所属がロジャー海賊団系のときのみ（クリークのギンは対象外）。"""
    if c.get("name") != "ギン":
        return False
    aff = str(c.get("affiliation", "") or "")
    return "ロジャー海賊団" in aff or "ロジャー" in aff


def merge_appearances_lists(*lists: list[dict] | None) -> list[dict]:
    by_ep: dict[int, str] = {}
    for lst in lists:
        for a in lst or []:
            if not isinstance(a, dict) or "episode" not in a:
                continue
            ep = int(a["episode"])
            if ep not in by_ep:
                by_ep[ep] = str(a.get("title", "") or "")
    return [{"episode": ep, "title": by_ep[ep]} for ep in sorted(by_ep)]


def merge_covers_lists(*lists: list[dict] | None) -> list[dict]:
    by_ep: dict[int, str] = {}
    for lst in lists:
        for a in lst or []:
            if not isinstance(a, dict) or "episode" not in a:
                continue
            ep = int(a["episode"])
            t = str(a.get("title", "") or "")
            if ep not in by_ep and t:
                by_ep[ep] = t
    return [{"episode": ep, "title": by_ep[ep]} for ep in sorted(by_ep)]


def consolidate_kyo_duplicates(chars: list[dict], log: list[str]) -> None:
    kyo = [c for c in chars if isinstance(c, dict) and c.get("name") == "凶"]
    if len(kyo) <= 1:
        return
    prefer = next((c for c in kyo if int(c.get("id", 0)) == 923), None)
    primary = prefer or min(kyo, key=lambda x: int(x["id"]))
    others = [c for c in kyo if c is not primary]
    apps = [primary.get("appearances")]
    covs = [primary.get("covers")]
    for o in others:
        apps.append(o.get("appearances"))
        covs.append(o.get("covers"))
    primary["appearances"] = merge_appearances_lists(*apps)
    merged_cov = merge_covers_lists(*covs)
    primary["covers"] = merged_cov if merged_cov else primary.get("covers", [])
    eps = [int(x["episode"]) for x in primary.get("appearances") or [] if isinstance(x, dict)]
    if eps:
        primary["firstAppearance"] = min(eps)
    remove_ids = {int(o["id"]) for o in others}
    chars[:] = [c for c in chars if not (isinstance(c, dict) and int(c.get("id", -1)) in remove_ids)]
    log.append(f"凶の重複 {len(others)} 件を id {primary['id']} に統合")


def patch_standard_names(obj: object, rename_by_norm: dict[str, str], log: list[str]) -> None:
    if isinstance(obj, dict):
        if "name" in obj and isinstance(obj["name"], str):
            nk = normalize(obj["name"])
            if nk in rename_by_norm:
                new_name = rename_by_norm[nk]
                if obj["name"] != new_name:
                    log.append(f"{obj['name']} -> {new_name}")
                    obj["name"] = new_name
        for v in obj.values():
            patch_standard_names(v, rename_by_norm, log)
    elif isinstance(obj, list):
        for item in obj:
            patch_standard_names(item, rename_by_norm, log)


def fix_roger_gin_to_kyo(chars: list[dict], log: list[str]) -> None:
    for c in chars:
        if not isinstance(c, dict):
            continue
        nm = c.get("name", "")
        if nm == "ギン（ロジャー海賊団）" or is_roger_crew_gin(c):
            if nm != "凶":
                log.append(f"{nm} -> 凶")
            c["name"] = "凶"
    consolidate_kyo_duplicates(chars, log)


def run_fix() -> None:
    with CHAR_PATH.open(encoding="utf-8") as f:
        chars: list[dict] = json.load(f)

    log: list[str] = []

    fix_roger_gin_to_kyo(chars, log)
    patch_standard_names(chars, RENAME_BY_NORM, log)

    chars.sort(key=lambda x: int(x.get("id", 0)))

    with CHAR_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)
        f.write("\n")

    for line in sorted(set(log)):
        print(f"✅ '{line}'")

    n_rename = sum(1 for x in log if " -> " in x and "統合" not in x)
    print(f"\n完了！ 名前変更 {n_rename} 件（凶の統合ログは別行）。")


if __name__ == "__main__":
    run_fix()
