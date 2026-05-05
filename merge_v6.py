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
    検索用キー:
    - NFKC
    - 空白除去
    - 中点除去（ボン・クレー系）
    - 引用符ゆれを軽く吸収（〝〟“”）
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
    """
    appearances: [{episode,title}, ...]
    - episode 重複は統合
    - title は非空/長い方優先
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


@dataclass(frozen=True)
class MergeSpec:
    left: str
    right: str
    final_name: str


def parse_spec_line(line: str) -> MergeSpec:
    """
    入力:
      "A / B"
      "A / B → C"
    規則:
      final_name は通常 left
      → があれば矢印後
    """
    raw = (line or "").strip()
    if "→" in raw:
        before, after = raw.split("→", 1)
        after = after.strip()
        raw = before.strip()
        left, right = [x.strip() for x in raw.split("/", 1)]
        return MergeSpec(left=left, right=right, final_name=after)
    left, right = [x.strip() for x in raw.split("/", 1)]
    return MergeSpec(left=left, right=right, final_name=left)


def find_single_id_by_name(chars: list[dict], query: str) -> int:
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


def handle_thumbnails(thumb_dir: Path, survivor_id: int, removed_id: int) -> str:
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


def main() -> int:
    ap = argparse.ArgumentParser(description="指定名ペアを統合し thumbnails を整理（v6）")
    ap.add_argument("--characters", default="src/data/characters.json")
    ap.add_argument("--thumb-dir", default="public/images/thumbnails")
    args = ap.parse_args()

    char_path = Path(args.characters)
    thumb_dir = Path(args.thumb_dir)

    chars = json.loads(char_path.read_text(encoding="utf-8"))
    if not isinstance(chars, list):
        raise SystemExit("characters.json は配列である必要があります")

    specs_raw = [
        "シャーロット・ローラ / ローラ",
        "カポネ・ベッジ / カポネ・ギャングベッジ",
        "カポネ・ペッツ / カポネ・ギャングペッツ",
        "ユースタス・キッド / ユースタス・キャプテンキッド",
        "トラファルガー・ロー（トラファルガー・Ｄ・ワーテル・ロー） / トラファルガー・ロー",
        "ロズワード・チャルロス聖 / チャルロス",
        "サディちゃん / サディ",
        "リップ・〝サービス〟・ドウティ / リップ・サービス・ドウティ",
        "マチェーテのルン / ルン",
        "タンク・レパント / タンク・レパンド",
        "ドンキホーテ・ロシナンテ(コラソン) / コラソン",
        "アルベル(キング) / キング",
        "オニ丸(牛鬼丸) / 牛鬼丸",
        "コンスロット / こんすろっと",
        "霜月康イエ(トの康) / トの康",
        "アシュラ童子(酒天丸) / 酒天丸",
        "お鶴 / 鶴",
        "菊之丞(お菊) / 菊",
        "お玉 / 玉",
        "ヒョウ五郎 / ヒョウじい",
        "黒炭オロチ / オロチ",
        "光月日和(小紫) / 小紫",
        "慰霊刃のフガー / フガー",
        "ブルブルのプルル / プルル",
        "ポンスキー / ボンスキー",
        "ベガパンク PUNK03｢想｣ / エジソン → ベガパンク PUNK03｢想｣（エジソン）",
        "Dr.ナコー / ナコー",
        "ベガパンク PUNK06｢欲｣ / ヨーク → ベガパンク PUNK06｢欲｣（ヨーク）",
        "ネフェルタリ・D・リリィ / ネフェルタリ・リリィ",
        "ベガパンク PUNK02｢悪｣ / リリス → ベガパンク PUNK02｢悪｣（リリス）",
        "ベガパンク PUNK05｢暴｣ / アトラス → ベガパンク PUNK05｢暴｣（アトラス）",
        "アン・ゼンカイーナ / アン・ゼンカイナ",
        "ベガパンク PUNK01｢正｣ / シャカ → ベガパンク PUNK01｢正｣（シャカ）",
        "ベガパンク PUNK04｢知｣ / ピタゴラス → ベガパンク PUNK04｢知｣（ピタゴラス）",
        "〝ハウリング〟ガブ / ガブ",
    ]
    specs = [parse_spec_line(x) for x in specs_raw]

    removed_ids: set[int] = set()
    merged = 0
    missing: list[str] = []
    thumb_actions: dict[str, int] = {"renamed": 0, "deleted": 0, "none": 0}

    # map id->char
    by_id: dict[int, dict] = {}
    for c in chars:
        if isinstance(c, dict):
            try:
                by_id[int(c.get("id"))] = c
            except Exception:
                pass

    for spec in specs:
        # refresh lookup to avoid removed ones
        live_chars = [c for c in chars if isinstance(c, dict) and int(c.get("id", -1)) not in removed_ids]
        try:
            id1 = find_single_id_by_name(live_chars, spec.left)
            id2 = find_single_id_by_name(live_chars, spec.right)
        except KeyError as e:
            missing.append(f"{spec.left} / {spec.right}: {e}")
            continue

        survivor_id, removed_id = (id1, id2) if id1 < id2 else (id2, id1)
        if survivor_id in removed_ids or removed_id in removed_ids:
            continue

        survivor = by_id.get(survivor_id)
        removed = by_id.get(removed_id)
        if survivor is None or removed is None:
            missing.append(f"{spec.left} / {spec.right}: id not found")
            continue

        merge_two(survivor, removed, spec.final_name)
        removed_ids.add(removed_id)
        merged += 1

        act = handle_thumbnails(thumb_dir, survivor_id, removed_id)
        thumb_actions[act] = thumb_actions.get(act, 0) + 1

    if removed_ids:
        chars = [c for c in chars if not (isinstance(c, dict) and int(c.get("id", -1)) in removed_ids)]
        chars.sort(key=lambda x: int(str(x.get("id", 0)) or 0) if isinstance(x, dict) else 0)
        char_path.write_text(json.dumps(chars, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

    print(f"統合した総件数: {merged}")
    print(f"画像: renamed={thumb_actions.get('renamed',0)} deleted={thumb_actions.get('deleted',0)} none={thumb_actions.get('none',0)}")
    if missing:
        print("見つからずスキップした項目:")
        for m in missing:
            print(f"  - {m}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

