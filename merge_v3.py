#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import unicodedata
from pathlib import Path
from typing import Any, Iterable


def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "").strip())


def is_empty_value(v: Any) -> bool:
    if v is None:
        return True
    if v == "":
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
    items = []
    for x in la + lb:
        if isinstance(x, str):
            t = x.strip()
            if t:
                items.append(t)
    return uniq_preserve(items)


def merge_appearances(a: Any, b: Any) -> list[dict]:
    """
    appearances: [{episode, title}, ...]
    - episode が同じものは 1つにまとめる（title は長い方/非空を優先）
    - episode 昇順にソート
    """
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


def choose_longer_name(n1: str, n2: str) -> str:
    a = nfkc(n1)
    b = nfkc(n2)
    return b if len(b) > len(a) else a


def load_chars(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


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
    # name: 長い方へ
    survivor["name"] = choose_longer_name(str(survivor.get("name") or ""), str(removed.get("name") or ""))

    # appearances / arcs / abilities
    if "appearances" in survivor or "appearances" in removed:
        survivor["appearances"] = merge_appearances(survivor.get("appearances"), removed.get("appearances"))

    if "arcs" in survivor or "arcs" in removed:
        survivor["arcs"] = merge_string_list(survivor.get("arcs"), removed.get("arcs"))

    if "abilities" in survivor or "abilities" in removed:
        survivor["abilities"] = merge_string_list(survivor.get("abilities"), removed.get("abilities"))

    # その他: survivor が空のフィールドを removed から補完
    for k, v in removed.items():
        if k == "id":
            continue
        if k in ("name", "appearances", "arcs", "abilities"):
            continue
        if k not in survivor or is_empty_value(survivor.get(k)):
            if not is_empty_value(v):
                survivor[k] = v


def pair_key(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def resolve_name_pairs(chars: list[dict]) -> list[tuple[int, int]]:
    """
    追加指定: 「凶」と「凶（銀斧）」を名前検索して統合
    実データでは '凶(銀斧)' のように半角括弧の可能性もあるので NFKC で寄せる。
    """
    id_kyo: int | None = None
    id_kyo_ginpu: int | None = None
    for c in chars:
        if not isinstance(c, dict):
            continue
        try:
            cid = int(c.get("id"))
        except Exception:
            continue
        nm = nfkc(str(c.get("name") or ""))
        if nm == "凶":
            id_kyo = cid
        if nm in ("凶(銀斧)", "凶（銀斧）"):
            id_kyo_ginpu = cid
    if id_kyo is not None and id_kyo_ginpu is not None:
        return [pair_key(id_kyo, id_kyo_ginpu)]
    return []


def handle_thumbnails(thumb_dir: Path, survivor_id: int, removed_id: int) -> tuple[int, int, int]:
    """
    returns: (renamed, deleted, untouched)
    """
    s = thumb_dir / f"{survivor_id}.webp"
    r = thumb_dir / f"{removed_id}.webp"
    renamed = deleted = untouched = 0

    if r.exists() and not s.exists():
        s.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(r), str(s))
        renamed += 1
    elif r.exists() and s.exists():
        r.unlink()
        deleted += 1
    else:
        untouched += 1

    return renamed, deleted, untouched


def main() -> int:
    ap = argparse.ArgumentParser(description="characters.json の重複統合 + thumbnails 整理")
    ap.add_argument("--characters", default="src/data/characters.json")
    ap.add_argument("--thumb-dir", default="public/images/thumbnails")
    args = ap.parse_args()

    char_path = Path(args.characters)
    thumb_dir = Path(args.thumb_dir)

    chars = load_chars(char_path)
    by_id = index_by_id(chars)

    # 指定ペア（ユーザー提示）
    raw_pairs = [
        (613, 863),
        (664, 825),
        (685, 881),
        (748, 791),
        (768, 813),
        (71, 960),
        (76, 965),
        (98, 1185),
        (100, 1183),
        (312, 1076),
        (321, 1140),
        (361, 1096),
        (426, 1103),
        (570, 1109),
    ]
    pairs = [pair_key(a, b) for a, b in raw_pairs]
    pairs += resolve_name_pairs(chars)
    pairs = uniq_preserve(pairs)

    merged_count = 0
    thumb_renamed = 0
    thumb_deleted = 0
    thumb_untouched = 0
    missing_ids: list[tuple[int, int]] = []

    removed_ids: set[int] = set()

    for a, b in pairs:
        if a in removed_ids or b in removed_ids:
            continue
        survivor_id, removed_id = a, b  # a<b
        survivor = by_id.get(survivor_id)
        removed = by_id.get(removed_id)
        if survivor is None or removed is None:
            missing_ids.append((survivor_id, removed_id))
            continue

        merge_two(survivor, removed)
        removed_ids.add(removed_id)
        merged_count += 1

        rn, dl, ut = handle_thumbnails(thumb_dir, survivor_id, removed_id)
        thumb_renamed += rn
        thumb_deleted += dl
        thumb_untouched += ut

    if removed_ids:
        chars = [c for c in chars if not (isinstance(c, dict) and int(c.get("id")) in removed_ids)]
        chars.sort(key=lambda x: int(str(x.get("id", 0)) or 0))
        char_path.write_text(json.dumps(chars, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    print(f"統合した件数: {merged_count}")
    print(f"画像リネーム: {thumb_renamed}")
    print(f"画像削除: {thumb_deleted}")
    print(f"画像変更なし: {thumb_untouched}")
    if removed_ids:
        print(f"削除したID数: {len(removed_ids)}")
    if missing_ids:
        print("見つからなかったIDペア:")
        for a, b in missing_ids:
            print(f"  - {a} / {b}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

