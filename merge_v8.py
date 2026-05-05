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
    """
    検索用キー:
    - NFKC
    - 空白除去
    - 中点除去
    - 引用符ゆれを軽く吸収（〝〟“”など）
    """
    t = nfkc(s)
    t = _SPACE_RE.sub("", t)
    t = t.replace("・", "")
    for ch in ["〝", "〟", "“", "”", "『", "』", "「", "」"]:
        t = t.replace(ch, "")
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


def ids_by_name(chars: list[dict], query: str) -> list[int]:
    """
    指定名に一致する id を全件返す（NFKC完全一致優先。無ければキー一致）。
    """
    q_nfkc = nfkc(query)
    q_key = name_key(query)
    exact: list[int] = []
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
            exact.append(cid)
        if name_key(nm) == q_key:
            key_match.append(cid)
    if exact:
        return sorted(set(exact))
    if key_match:
        return sorted(set(key_match))
    return []


def find_single_id_by_name(chars: list[dict], query: str) -> int:
    ids = ids_by_name(chars, query)
    if not ids:
        raise KeyError(f"名前が見つかりません: {query}")
    return min(ids)


def merge_two(survivor: dict, removed: dict, final_name: str) -> None:
    survivor["name"] = nfkc(final_name)
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


def handle_thumbnails_merge(thumb_dir: Path, survivor_id: int, removed_id: int) -> str:
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


def delete_thumbnail_if_exists(thumb_dir: Path, cid: int) -> bool:
    p = thumb_dir / f"{cid}.webp"
    if p.exists():
        p.unlink()
        return True
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="characters.json の削除+統合（v8）+ thumbnails 整理")
    ap.add_argument("--characters", default="src/data/characters.json")
    ap.add_argument("--thumb-dir", default="public/images/thumbnails")
    args = ap.parse_args()

    char_path = Path(args.characters)
    thumb_dir = Path(args.thumb_dir)

    chars = json.loads(char_path.read_text(encoding="utf-8"))
    if not isinstance(chars, list):
        raise SystemExit("characters.json は配列である必要があります")

    by_id: dict[int, dict] = {}
    for c in chars:
        if isinstance(c, dict):
            try:
                by_id[int(c.get("id"))] = c
            except Exception:
                pass

    removed_ids: set[int] = set()

    def live_chars() -> list[dict]:
        return [c for c in chars if isinstance(c, dict) and int(c.get("id", -1)) not in removed_ids]

    # 1) deletions
    delete_names = ["ツメゲリ部隊", "怪力デストロイヤーズ", "尾田栄一郎"]
    deleted_chars: list[tuple[int, str]] = []
    deleted_thumbs = 0
    for nm in delete_names:
        ids = ids_by_name(live_chars(), nm)
        for cid in ids:
            if cid in removed_ids:
                continue
            removed_ids.add(cid)
            deleted_chars.append((cid, nm))
            if delete_thumbnail_if_exists(thumb_dir, cid):
                deleted_thumbs += 1

    # 2) merges (left name wins)
    merges = [("ヤガラ", "ヤガラブル"), ("スルメ", "クラーケン")]
    merged_results: list[dict] = []
    thumb_actions: dict[str, int] = {"renamed": 0, "deleted": 0, "none": 0}
    missing: list[str] = []

    for left, right in merges:
        try:
            id1 = find_single_id_by_name(live_chars(), left)
            id2 = find_single_id_by_name(live_chars(), right)
        except KeyError as e:
            missing.append(f"MERGE {left} / {right}: {e}")
            continue

        survivor_id, removed_id = (id1, id2) if id1 < id2 else (id2, id1)
        if survivor_id in removed_ids or removed_id in removed_ids:
            continue
        survivor = by_id.get(survivor_id)
        removed = by_id.get(removed_id)
        if survivor is None or removed is None:
            missing.append(f"MERGE {left} / {right}: id not found")
            continue

        merge_two(survivor, removed, left)
        removed_ids.add(removed_id)
        act = handle_thumbnails_merge(thumb_dir, survivor_id, removed_id)
        thumb_actions[act] = thumb_actions.get(act, 0) + 1

        merged_results.append(
            {
                "pair": f"{left} / {right}",
                "survivor_id": survivor_id,
                "removed_id": removed_id,
                "final_name": left,
            }
        )

    # write back
    if removed_ids:
        chars = [c for c in chars if not (isinstance(c, dict) and int(c.get("id", -1)) in removed_ids)]
    chars.sort(key=lambda x: int(str(x.get("id", 0)) or 0) if isinstance(x, dict) else 0)
    char_path.write_text(json.dumps(chars, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    print(f"削除（キャラ）件数: {len(deleted_chars)}")
    print(f"削除（画像）件数: {deleted_thumbs}")
    if deleted_chars:
        print("削除したID:")
        for cid, nm in deleted_chars:
            print(f"  - {cid} {nm}")

    print(f"統合（マージ）件数: {len(merged_results)}")
    for r in merged_results:
        print(f"  - {r['pair']}: {r['survivor_id']} を存続 / {r['removed_id']} を削除 → name='{r['final_name']}'")
    print(f"画像(マージ): renamed={thumb_actions.get('renamed',0)} deleted={thumb_actions.get('deleted',0)} none={thumb_actions.get('none',0)}")

    if missing:
        print("見つからずスキップした項目:")
        for m in missing:
            print(f"  - {m}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

