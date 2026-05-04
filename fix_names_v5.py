#!/usr/bin/env python3
"""名称置換と ダイナ→コロン の統合（appearances / covers マージ、重複話数削除）。"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHAR_PATH = ROOT / "src/data/characters.json"


def normalize(name: str) -> str:
    return re.sub(r"[・\s\-]", "", (name or "").strip())


RENAME_BY_NORM: dict[str, str] = {
    normalize("アイギル"): "エーギル",
    normalize("ロッシュ"): "ロシュ",
    normalize("グラットバニー"): "グルトバニー",
    normalize("ドウロ"): "ロード",
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
    """同一話は primary のタイトルを優先し、無い話のみ secondary から追加。"""
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


def patch_coappearances_daina_to_colon(obj: object, old_id: int, new_id: int) -> int:
    """キャラ参照の coAppearances 風 {id, name, count} のみ id843+ダイナ を更新。"""
    n = 0
    if isinstance(obj, dict):
        if (
            obj.get("id") == old_id
            and "count" in obj
            and isinstance(obj.get("name"), str)
            and normalize(obj["name"]) == normalize("ダイナ")
        ):
            obj["id"] = new_id
            obj["name"] = "コロン"
            n += 1
        for v in obj.values():
            n += patch_coappearances_daina_to_colon(v, old_id, new_id)
    elif isinstance(obj, list):
        for item in obj:
            n += patch_coappearances_daina_to_colon(item, old_id, new_id)
    return n


def merge_daina_into_colon(chars: list[dict], log: list[str]) -> None:
    target = next(
        (c for c in chars if isinstance(c, dict) and normalize(c.get("name", "")) == normalize("コロン")),
        None,
    )
    source = next(
        (c for c in chars if isinstance(c, dict) and normalize(c.get("name", "")) == normalize("ダイナ")),
        None,
    )
    if not target or not source:
        log.append(
            f"統合スキップ: コロン={'見つかった' if target else 'なし'}, ダイナ={'見つかった' if source else 'なし'}"
        )
        return

    tid, sid = int(target["id"]), int(source["id"])
    target["appearances"] = merge_episode_lists(target.get("appearances"), source.get("appearances"))
    target["covers"] = merge_episode_lists(target.get("covers"), source.get("covers"))

    eps = [int(x["episode"]) for x in target.get("appearances") or [] if isinstance(x, dict)]
    if eps:
        target["firstAppearance"] = min(eps)

    n_co = patch_coappearances_daina_to_colon(chars, sid, tid)
    chars[:] = [c for c in chars if not (isinstance(c, dict) and int(c.get("id", -1)) == sid)]

    log.append(
        f"統合完了: ダイナ(id={sid}) -> コロン(id={tid}) / "
        f"appearances {len(target.get('appearances') or [])} 件, "
        f"covers {len(target.get('covers') or [])} 件 / coAppearances更新 {n_co} 件"
    )


def run_fix() -> None:
    with CHAR_PATH.open(encoding="utf-8") as f:
        chars: list[dict] = json.load(f)

    log: list[str] = []

    patch_names(chars, RENAME_BY_NORM, log)
    merge_daina_into_colon(chars, log)

    chars.sort(key=lambda x: int(x.get("id", 0)))

    with CHAR_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)
        f.write("\n")

    for line in log:
        print(f"✅ {line}")

    print("\n修正と統合が完了しました。")


if __name__ == "__main__":
    run_fix()
