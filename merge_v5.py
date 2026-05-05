#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import unicodedata
from pathlib import Path
from typing import Any, Iterable


def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "").strip())


_SPACE_RE = re.compile(r"[ \t\u3000]+")


def name_key(s: str) -> str:
    t = nfkc(s)
    t = _SPACE_RE.sub("", t)
    t = t.replace("・", "")
    return t


def is_empty_value(v: Any) -> bool:
    if v is None or v == "":
        return True
    if isinstance(v, (list, tuple, set, dict)) and len(v) == 0:
        return True
    return False


def uniq_preserve(seq: Iterable[Any]) -> list[Any]:
    out: list[Any] = []
    seen: set[Any] = set()
    for x in seq:
        key = x if isinstance(x, (str, int, float, tuple)) else json.dumps(x, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        out.append(x)
    return out


def merge_string_list(a: Any, b: Any) -> list[str]:
    la = a if isinstance(a, list) else []
    lb = b if isinstance(b, list) else []
    items: list[str] = []
    for x in la + lb:
        if isinstance(x, str):
            t = x.strip()
            if t:
                items.append(t)
    return uniq_preserve(items)


def merge_appearances(a: Any, b: Any) -> list[dict]:
    la = a if isinstance(a, list) else []
    lb = b if isinstance(b, list) else []
    mp: dict[int, dict] = {}
    for row in la + lb:
        if not isinstance(row, dict):
            continue
        ep = row.get("episode")
        try:
            epi = int(ep)
        except Exception:
            continue
        title = str(row.get("title") or "").strip()
        cur = mp.get(epi)
        if cur is None:
            mp[epi] = {"episode": epi, "title": title}
        else:
            cur_title = str(cur.get("title") or "").strip()
            if not cur_title and title:
                cur["title"] = title
            elif title and len(title) > len(cur_title):
                cur["title"] = title
    return [mp[k] for k in sorted(mp.keys())]


def choose_longer_name(a: str, b: str) -> str:
    na = nfkc(a)
    nb = nfkc(b)
    return nb if len(nb) > len(na) else na


def index_by_id(chars: list[dict]) -> dict[int, dict]:
    mp: dict[int, dict] = {}
    for c in chars:
        if not isinstance(c, dict):
            continue
        try:
            cid = int(c.get("id"))
        except Exception:
            continue
        mp[cid] = c
    return mp


def merge_two(survivor: dict, removed: dict) -> None:
    survivor["name"] = choose_longer_name(str(survivor.get("name") or ""), str(removed.get("name") or ""))
    survivor["appearances"] = merge_appearances(survivor.get("appearances"), removed.get("appearances"))
    survivor["arcs"] = merge_string_list(survivor.get("arcs"), removed.get("arcs"))
    survivor["abilities"] = merge_string_list(survivor.get("abilities"), removed.get("abilities"))

    for k, v in removed.items():
        if k == "id":
            continue
        if k in ("name", "appearances", "arcs", "abilities"):
            continue
        if k not in survivor or is_empty_value(survivor.get(k)):
            if not is_empty_value(v):
                survivor[k] = v


def handle_thumbnails(thumb_dir: Path, survivor_id: int, removed_id: int) -> str:
    """
    returns: renamed / deleted / none
    """
    s = thumb_dir / f"{survivor_id}.webp"
    r = thumb_dir / f"{removed_id}.webp"
    if r.exists() and not s.exists():
        s.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(r), str(s))
        return "renamed"
    if r.exists() and s.exists():
        r.unlink()
        return "deleted"
    return "none"


def find_id_by_name(chars: list[dict], query: str) -> int:
    q_nfkc = nfkc(query)
    q_key = name_key(query)

    exact_nfkc: list[int] = []
    key_match: list[int] = []

    for c in chars:
        if not isinstance(c, dict):
            continue
        try:
            cid = int(c.get("id"))
        except Exception:
            continue
        nm = str(c.get("name") or "")
        if nfkc(nm) == q_nfkc:
            exact_nfkc.append(cid)
        if name_key(nm) == q_key:
            key_match.append(cid)

    if exact_nfkc:
        return min(exact_nfkc)
    if key_match:
        return min(key_match)
    raise KeyError(f"名前が見つかりません: {query}")


def delete_by_name(chars: list[dict], target_name: str) -> tuple[list[dict], list[int]]:
    tgt = nfkc(target_name)
    removed: list[int] = []
    kept: list[dict] = []
    for c in chars:
        if not isinstance(c, dict):
            kept.append(c)
            continue
        if nfkc(str(c.get("name") or "")) == tgt:
            try:
                removed.append(int(c.get("id")))
            except Exception:
                pass
            continue
        kept.append(c)
    return kept, sorted(removed)


def main() -> int:
    ap = argparse.ArgumentParser(description="characters.json の統合（指定名）+ 削除（指定名）+ thumbnails 整理")
    ap.add_argument("--characters", default="src/data/characters.json")
    ap.add_argument("--thumb-dir", default="public/images/thumbnails")
    args = ap.parse_args()

    char_path = Path(args.characters)
    thumb_dir = Path(args.thumb_dir)

    chars = json.loads(char_path.read_text(encoding="utf-8"))
    if not isinstance(chars, list):
        raise SystemExit("characters.json は配列である必要があります")

    # 1) merge: シャンドラの長老 + シャンディアの酋長
    id_a = find_id_by_name(chars, "シャンドラの長老")
    id_b = find_id_by_name(chars, "シャンディアの酋長")
    survivor_id, removed_id = (id_a, id_b) if id_a < id_b else (id_b, id_a)

    by_id = index_by_id(chars)
    survivor = by_id[survivor_id]
    removed = by_id[removed_id]

    merge_two(survivor, removed)
    # 念のため指定どおり最終名を固定（長い方のはず）
    survivor["name"] = "シャンディアの酋長"

    thumb_action = handle_thumbnails(thumb_dir, survivor_id, removed_id)

    # 2) delete: みなもと
    chars, deleted_ids = delete_by_name(chars, "みなもと")

    # remove merged removed_id
    chars = [c for c in chars if not (isinstance(c, dict) and int(c.get("id", -1)) == removed_id)]

    # sort & save
    chars.sort(key=lambda x: int(str(x.get("id", 0)) or 0) if isinstance(x, dict) else 0)
    char_path.write_text(json.dumps(chars, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    print(f"[MERGED] survivor={survivor_id} removed={removed_id} name='{survivor['name']}' thumb={thumb_action}")
    if deleted_ids:
        print(f"[DELETED] name='みなもと' ids={', '.join(map(str, deleted_ids))}")
    else:
        print("[DELETED] name='みなもと' ids=なし")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

