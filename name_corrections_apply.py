"""
characters.json 保存直前に適用する名前補正（name_corrections.json）。

- merges: ソースをターゲットへ appearances/covers を合流し、ソース行を削除。
  ターゲットが無い場合はソースの name のみターゲット表記へ変更（同一人物の別名統合）。
- renames: JSON 内のすべての name フィールドをキー照合で置換（正規化は ・ 空白 - ★ を無視）。
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

ROOT = os.path.dirname(os.path.abspath(__file__))
CORRECTIONS_PATH = os.path.join(ROOT, "src", "data", "name_corrections.json")


def normalize_key(name: str) -> str:
    return re.sub(r"[・\s\-★]", "", (name or "").strip())


def merge_episode_lists(
    primary: list[dict] | None, secondary: list[dict] | None
) -> list[dict]:
    by_ep: dict[int, str] = {}
    for a in primary or []:
        if not isinstance(a, dict) or "episode" not in a:
            continue
        ep = int(a["episode"])
        t = str(a.get("title", "") or "")
        if ep not in by_ep and t:
            by_ep[ep] = t
    for a in secondary or []:
        if not isinstance(a, dict) or "episode" not in a:
            continue
        ep = int(a["episode"])
        if ep not in by_ep:
            t = str(a.get("title", "") or "")
            if t:
                by_ep[ep] = t
    return [{"episode": ep, "title": by_ep[ep]} for ep in sorted(by_ep)]


def patch_coappearances_id(obj: Any, old_id: int, new_id: int, new_name: str) -> int:
    n = 0
    if isinstance(obj, dict):
        if obj.get("id") == old_id and "count" in obj and isinstance(obj.get("name"), str):
            obj["id"] = new_id
            obj["name"] = new_name
            n += 1
        for v in obj.values():
            n += patch_coappearances_id(v, old_id, new_id, new_name)
    elif isinstance(obj, list):
        for item in obj:
            n += patch_coappearances_id(item, old_id, new_id, new_name)
    return n


def find_char(chars: list[dict], label: str) -> dict | None:
    want = normalize_key(label)
    for c in chars:
        if isinstance(c, dict) and normalize_key(str(c.get("name", ""))) == want:
            return c
    return None


def merge_chars_list(chars: list[dict], source_label: str, target_label: str) -> None:
    target = find_char(chars, target_label)
    source = find_char(chars, source_label)
    if not source:
        return
    if not target:
        source["name"] = target_label
        eps = [
            int(x["episode"])
            for x in source.get("appearances") or []
            if isinstance(x, dict) and "episode" in x
        ]
        if eps:
            source["firstAppearance"] = min(eps)
        return
    if target is source:
        return
    tid, sid = int(target["id"]), int(source["id"])
    target["appearances"] = merge_episode_lists(
        target.get("appearances"), source.get("appearances")
    )
    target["covers"] = merge_episode_lists(target.get("covers"), source.get("covers"))
    eps = [
        int(x["episode"])
        for x in target.get("appearances") or []
        if isinstance(x, dict) and "episode" in x
    ]
    if eps:
        target["firstAppearance"] = min(eps)
    patch_coappearances_id(chars, sid, tid, str(target.get("name", "")))
    chars[:] = [c for c in chars if not (isinstance(c, dict) and int(c.get("id", -1)) == sid)]


def patch_names_recursive(obj: Any, rename_norm_to_new: dict[str, str]) -> None:
    if isinstance(obj, dict):
        if "name" in obj and isinstance(obj["name"], str):
            nk = normalize_key(obj["name"])
            if nk in rename_norm_to_new:
                new_name = rename_norm_to_new[nk]
                if obj["name"] != new_name:
                    obj["name"] = new_name
        for v in obj.values():
            patch_names_recursive(v, rename_norm_to_new)
    elif isinstance(obj, list):
        for item in obj:
            patch_names_recursive(item, rename_norm_to_new)


def sort_all_appearances(chars: list[dict]) -> None:
    for c in chars:
        apps = c.get("appearances")
        if isinstance(apps, list):
            apps.sort(
                key=lambda x: int(x["episode"])
                if isinstance(x.get("episode"), int)
                else int(str(x.get("episode", "0")))
            )


def apply_name_corrections(chars: list[dict]) -> None:
    if not os.path.isfile(CORRECTIONS_PATH):
        return
    with open(CORRECTIONS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    merges = data.get("merges") or {}
    renames = data.get("renames") or {}

    for source_label, target_label in merges.items():
        if not isinstance(source_label, str) or not isinstance(target_label, str):
            continue
        merge_chars_list(chars, source_label, target_label)

    rename_norm_to_new = {
        normalize_key(k): v for k, v in renames.items() if isinstance(k, str) and isinstance(v, str)
    }
    patch_names_recursive(chars, rename_norm_to_new)
    sort_all_appearances(chars)
