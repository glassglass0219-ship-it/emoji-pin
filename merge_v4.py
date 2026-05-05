#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "").strip())


_SPACE_RE = re.compile(r"[ \t\u3000]+")


def name_key(s: str) -> str:
    """
    名前検索用キー:
    - NFKC
    - 空白除去
    - 中点「・」除去（ボン・クレー vs ボンクレー）
    """
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


def choose_name(preferred: str | None, a: str, b: str) -> str:
    if preferred:
        return nfkc(preferred)
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


def merge_two(survivor: dict, removed: dict, preferred_name: str | None = None) -> None:
    survivor["name"] = choose_name(preferred_name, str(survivor.get("name") or ""), str(removed.get("name") or ""))

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


@dataclass(frozen=True)
class ThumbResult:
    action: str  # renamed / deleted / none
    src: str
    dst: str


def handle_thumbnails(thumb_dir: Path, survivor_id: int, removed_id: int) -> ThumbResult:
    s = thumb_dir / f"{survivor_id}.webp"
    r = thumb_dir / f"{removed_id}.webp"
    if r.exists() and not s.exists():
        s.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(r), str(s))
        return ThumbResult("renamed", str(r), str(s))
    if r.exists() and s.exists():
        r.unlink()
        return ThumbResult("deleted", str(r), str(s))
    return ThumbResult("none", str(r), str(s))


def find_single_id_by_name(chars: list[dict], query: str) -> int:
    """
    指定名に一致するキャラIDを1つ返す（複数ある場合は最小ID）。
    - NFKC + 空白/中点除去で照合
    - query そのものが見つからなければ、NFKCのみ完全一致も優先
    """
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


def delete_by_name(chars: list[dict], name: str) -> tuple[list[dict], list[int]]:
    target = nfkc(name)
    removed: list[int] = []
    kept: list[dict] = []
    for c in chars:
        if not isinstance(c, dict):
            kept.append(c)
            continue
        nm = nfkc(str(c.get("name") or ""))
        if nm == target:
            try:
                removed.append(int(c.get("id")))
            except Exception:
                removed.append(-1)
            continue
        kept.append(c)
    removed = [x for x in removed if x != -1]
    return kept, removed


def main() -> int:
    ap = argparse.ArgumentParser(description="名前指定の統合 + 指定名削除 + thumbnails 整理")
    ap.add_argument("--characters", default="src/data/characters.json")
    ap.add_argument("--thumb-dir", default="public/images/thumbnails")
    args = ap.parse_args()

    char_path = Path(args.characters)
    thumb_dir = Path(args.thumb_dir)

    chars = json.loads(char_path.read_text(encoding="utf-8"))
    if not isinstance(chars, list):
        raise SystemExit("characters.json は配列である必要があります")

    # (left_name, right_name, preferred_name_or_none)
    merges: list[tuple[str, str, str | None]] = [
        ("ボンクレー", "ベンサム(Mr.2・ボン・クレー)", None),
        ("Mr.1", "ダズ・ボーネス(Mr.1)", None),
        ("Mr.4", "ベーブ(Mr.4)", None),
        ("ヒッコシクラブ", "ハサミ", "ハサミ（ヒッコシクラブ）"),
        ("Mr.5", "ジェム(Mr.5)", None),
        ("Mr.3", "ギャルディーノ(Mr.3)", None),
    ]

    report_merges: list[dict[str, Any]] = []
    removed_ids: set[int] = set()

    for left, right, preferred in merges:
        # その時点の chars から検索（前の統合で消えた場合を避ける）
        live_chars = [c for c in chars if not (isinstance(c, dict) and int(c.get("id", -1)) in removed_ids)]
        try:
            id1 = find_single_id_by_name(live_chars, left)
            id2 = find_single_id_by_name(live_chars, right)
        except KeyError as e:
            report_merges.append(
                {"pair": f"{left} / {right}", "status": "skipped", "reason": str(e)}
            )
            continue

        survivor_id, removed_id = (id1, id2) if id1 < id2 else (id2, id1)
        if survivor_id in removed_ids or removed_id in removed_ids:
            report_merges.append(
                {"pair": f"{left} / {right}", "status": "skipped", "reason": "already removed by earlier merge"}
            )
            continue

        by_id = index_by_id(chars)
        survivor = by_id.get(survivor_id)
        removed = by_id.get(removed_id)
        if survivor is None or removed is None:
            report_merges.append(
                {"pair": f"{left} / {right}", "status": "skipped", "reason": "id not found in data"}
            )
            continue

        before_name = str(survivor.get("name") or "")
        merge_two(survivor, removed, preferred_name=preferred)
        after_name = str(survivor.get("name") or "")
        removed_ids.add(removed_id)

        thumb = handle_thumbnails(thumb_dir, survivor_id, removed_id)

        report_merges.append(
            {
                "pair": f"{left} / {right}",
                "status": "merged",
                "survivor_id": survivor_id,
                "removed_id": removed_id,
                "name_before": before_name,
                "name_after": after_name,
                "thumb_action": thumb.action,
                "thumb_src": thumb.src,
                "thumb_dst": thumb.dst,
            }
        )

    # 削除: 五老星（集団名）
    chars, deleted_gorosei_ids = delete_by_name(chars, "五老星")
    deleted_gorosei_ids = [i for i in deleted_gorosei_ids if i not in removed_ids]

    # 統合で削除するIDを反映
    if removed_ids:
        chars = [c for c in chars if not (isinstance(c, dict) and int(c.get("id", -1)) in removed_ids)]

    # ソートして保存
    chars.sort(key=lambda x: int(str(x.get("id", 0)) or 0) if isinstance(x, dict) else 0)
    char_path.write_text(json.dumps(chars, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    # 結果表示
    merged_ok = [r for r in report_merges if r.get("status") == "merged"]
    renamed = sum(1 for r in merged_ok if r.get("thumb_action") == "renamed")
    deleted = sum(1 for r in merged_ok if r.get("thumb_action") == "deleted")
    none = sum(1 for r in merged_ok if r.get("thumb_action") == "none")

    print(f"統合件数: {len(merged_ok)}")
    print(f"画像: renamed={renamed} deleted={deleted} none={none}")
    if deleted_gorosei_ids:
        print(f"削除(五老星) ID: {', '.join(map(str, sorted(deleted_gorosei_ids)))}")
    else:
        print("削除(五老星) ID: なし")
    print()
    for r in report_merges:
        if r.get("status") != "merged":
            print(f"[SKIP] {r.get('pair')}: {r.get('reason')}")
            continue
        print(
            f"[MERGED] {r['pair']} -> survivor={r['survivor_id']} removed={r['removed_id']} "
            f"name='{r['name_after']}' thumb={r['thumb_action']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

