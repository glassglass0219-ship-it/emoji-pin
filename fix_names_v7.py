#!/usr/bin/env python3
"""キャラ名の修正と アイアン・ジャイアント/ダルトン の統合（characters.json）。"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAR_PATH = ROOT / "src/data/characters.json"


def normalize(name: str) -> str:
    return re.sub(r"[・\s\-]", "", (name or "").strip())


RENAME_BY_NORM: dict[str, str] = {
    normalize("フィガーランド・シャムロック"): "フィガーランド・シャムロック聖",
    normalize("アン"): "アン・ゼンカイナ",
    normalize("ゴエン"): "ジャン・ゴエン",
    normalize("ウサギヘビ"): "うさぎヘビ",
    normalize("トルマン"): "トールマン",
    normalize("牛野"): "ウシアーノ",
    normalize("ヨモ"): "ヨモ牧師",
    normalize("コンセロット"): "コンスロット",
    normalize("ナコ"): "ナコー",
    normalize("シモツキ・コウシロウ"): "霜月コウシロウ",
    normalize("マンジャロ"): "マンジャロウ",
}


def patch_names(obj: object, rename_by_norm: dict[str, str], log: list[str]) -> None:
    if isinstance(obj, dict):
        if "name" in obj and isinstance(obj["name"], str):
            nk = normalize(obj["name"])
            if nk in rename_by_norm:
                new_name = rename_by_norm[nk]
                if obj["name"] != new_name:
                    log.append(f"改名: {obj['name']} -> {new_name}")
                    obj["name"] = new_name
        for v in obj.values():
            patch_names(v, rename_by_norm, log)
    elif isinstance(obj, list):
        for item in obj:
            patch_names(item, rename_by_norm, log)


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


def patch_coappearances_id(
    obj: object, old_id: int, new_id: int, new_name: str
) -> int:
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


def find_char(chars: list[dict], name: str) -> dict | None:
    for c in chars:
        if isinstance(c, dict) and normalize(c.get("name", "")) == normalize(name):
            return c
    return None


def merge_chars(
    chars: list[dict],
    source_label: str,
    target_label: str,
    log: list[str],
) -> None:
    target = find_char(chars, target_label)
    source = find_char(chars, source_label)
    if not source:
        log.append(f"統合スキップ: {source_label} が見つかりません")
        return
    if not target:
        log.append(f"統合スキップ: {target_label} が見つかりません（{source_label} は未削除）")
        return
    if target is source:
        return
    tid, sid = int(target["id"]), int(source["id"])
    target["appearances"] = merge_episode_lists(
        target.get("appearances"), source.get("appearances")
    )
    target["covers"] = merge_episode_lists(target.get("covers"), source.get("covers"))
    eps = [int(x["episode"]) for x in target.get("appearances") or [] if isinstance(x, dict)]
    if eps:
        target["firstAppearance"] = min(eps)
    n_co = patch_coappearances_id(chars, sid, tid, str(target.get("name", "")))
    chars[:] = [c for c in chars if not (isinstance(c, dict) and int(c.get("id", -1)) == sid)]
    log.append(
        f"統合完了: {source.get('name')}(id={sid}) -> {target.get('name')}(id={tid}) / "
        f"appearances {len(target.get('appearances') or [])} 件, "
        f"covers {len(target.get('covers') or [])} 件 / coAppearances更新 {n_co} 件"
    )


def run_fix() -> None:
    with CHAR_PATH.open(encoding="utf-8") as f:
        chars: list[dict] = json.load(f)

    log: list[str] = []

    merge_chars(chars, "アイアン・ジャイアント", "エメト", log)
    merge_chars(chars, "ダルトン", "ドルトン", log)
    patch_names(chars, RENAME_BY_NORM, log)

    chars.sort(key=lambda x: int(x.get("id", 0)))

    with CHAR_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)
        f.write("\n")

    for line in log:
        print(line)
    print("\nすべての修正・統合が完了しました。")


if __name__ == "__main__":
    run_fix()
