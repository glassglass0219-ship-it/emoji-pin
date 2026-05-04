#!/usr/bin/env python3
"""キャラ名の微調整、ゼウス/トサの統合、モクバ削除（characters.json）。"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAR_PATH = ROOT / "src/data/characters.json"


def normalize(name: str) -> str:
    return re.sub(r"[・\s\-★]", "", (name or "").strip())


RENAME_BY_NORM: dict[str, str] = {
    normalize("ニードル"): "針神",
    normalize("ギャブ"): "ガブ",
    normalize("湊"): "港友",
    normalize("イヤンエーノウ・チノデ"): "イヤンエーノウ・チノデ（表記確認）",
    normalize("アタッチ"): "アタっちゃん",
    normalize("ポムスキー"): "ポンスキー",
    normalize("ヒロ・ゴモン"): "ヒロ★ゴーモン",
    normalize("スキミタルタ"): "シミター太",
    normalize("アリス"): "アリーチェ",
    normalize("ゼウス・ブリーズテンポ"): "ゼウス",
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
    """coAppearances 風 {id, name, count} を old_id -> new_id に差し替え。"""
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
    if target and target is not source:
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
            f"統合完了: {source_label}(id={sid}) -> {target.get('name')}(id={tid}) / "
            f"appearances {len(target.get('appearances') or [])} 件, "
            f"covers {len(target.get('covers') or [])} 件 / coAppearances更新 {n_co} 件"
        )
        return

    # ターゲットが別レコードに無い場合は、ソースを改名して統合済みとする
    old_name = str(source.get("name", ""))
    source["name"] = target_label
    eps = [int(x["episode"]) for x in source.get("appearances") or [] if isinstance(x, dict)]
    if eps:
        source["firstAppearance"] = min(eps)
    log.append(
        f"統合（単独レコード改名）: {old_name}(id={source.get('id')}) -> {target_label} "
        f"/ appearances {len(source.get('appearances') or [])} 件"
    )


def delete_char(chars: list[dict], name: str, log: list[str]) -> None:
    before = len(chars)
    chars[:] = [
        c
        for c in chars
        if not (isinstance(c, dict) and normalize(c.get("name", "")) == normalize(name))
    ]
    removed = before - len(chars)
    if removed:
        log.append(f"削除: {name} ({removed} 件)")
    else:
        log.append(f"削除スキップ: {name} は見つかりませんでした")


def run_fix() -> None:
    with CHAR_PATH.open(encoding="utf-8") as f:
        chars: list[dict] = json.load(f)

    log: list[str] = []

    merge_chars(chars, "トサ", "土茶", log)
    merge_chars(chars, "ゼウス・ブリーズテンポ", "ゼウス", log)
    delete_char(chars, "モクバ", log)
    patch_names(chars, RENAME_BY_NORM, log)

    chars.sort(key=lambda x: int(x.get("id", 0)))

    with CHAR_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)
        f.write("\n")

    for line in log:
        print(line)
    print("\nすべての修正・統合・削除が完了しました。")


if __name__ == "__main__":
    run_fix()
