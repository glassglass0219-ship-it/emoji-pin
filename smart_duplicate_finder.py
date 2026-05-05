#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "").strip())


_SPACE_RE = re.compile(r"[ \t\u3000]+")


def norm_key(s: str) -> str:
    """
    比較キー:
    - Unicode NFKC
    - 空白類と中点を除去
    - 記号の揺れ（括弧/引用符など）を軽く落とす
    """
    t = nfkc(s)
    t = _SPACE_RE.sub("", t)
    t = t.replace("・", "")
    # たとえば “赤髪のシャンクス” の “ ” を除去
    for ch in ['"', "“", "”", "〝", "〟", "『", "』", "「", "」"]:
        t = t.replace(ch, "")
    return t


TITLE_PREFIXES = [
    "赤髪の",
    "麦わらの",
    "海賊王",
    "四皇",
    "大将",
    "元帥",
    "王下七武海",
    "世界最強の男",
]

MR_CODE_RE = re.compile(r"^mr\.?\s*(\d+)$", re.IGNORECASE)
MISS_CODE_RE = re.compile(r"^(?:ミス|miss)\.?\s*(\d+)$", re.IGNORECASE)


def is_numbered_code_name_like(nk: str) -> bool:
    """
    部分一致で誤爆しやすい「番号付きコードネーム」を判定。
    例: Mr.1 / Mr.13 / ミス13 など
    """
    t = (nk or "").strip().lower()
    return bool(MR_CODE_RE.match(t) or MISS_CODE_RE.match(t))


def strip_title_like_prefixes(name: str) -> str:
    t = nfkc(name)
    for p in TITLE_PREFIXES:
        if t.startswith(p):
            return t[len(p) :].strip()
    return t


PAREN_OPEN = "（"
PAREN_CLOSE = "）"


def extract_aliases_from_name(name: str) -> list[str]:
    """
    name 文字列から、括弧内やスラッシュ表記の別名候補を抽出。
    例:
      "ギャルディーノ（Mr.3）" -> ["ギャルディーノ", "Mr.3"]
      "イガラム（Mr.8/イガラッポイ）" -> ["イガラム", "Mr.8", "イガラッポイ"]
    """
    out: list[str] = []
    raw = nfkc(name)
    if not raw:
        return out

    out.append(raw)

    if PAREN_OPEN in raw and raw.endswith(PAREN_CLOSE):
        before, inside = raw.split(PAREN_OPEN, 1)
        inside = inside[: -1]  # drop close
        before = before.strip()
        if before:
            out.append(before)
        # split by "/" "・" "／"
        for part in re.split(r"[\/／]", inside):
            p = part.strip()
            if p:
                out.append(p)

    # “ルーシー” など引用符だけの表記もあるので、引用符は norm_key で落とす
    # ただしここでは raw を保持しておく
    # unique
    uniq: list[str] = []
    seen = set()
    for s in out:
        k = norm_key(s)
        if not k:
            continue
        if k in seen:
            continue
        seen.add(k)
        uniq.append(s)
    return uniq


def tokens_for_partial(name: str) -> set[str]:
    """
    部分一致用のトークン集合。
    - 括弧内/外の別名も含める
    - 記号で分割しつつ、短すぎるものは除外
    """
    toks: set[str] = set()
    for cand in extract_aliases_from_name(name):
        base = norm_key(cand)
        if not base:
            continue
        # 記号で分割
        for part in re.split(r"[()（）\[\]【】・/／,，,。\.・\-ー—\s]+", nfkc(cand)):
            p = norm_key(part)
            # 2文字だと誤爆が多い（例: メリー/○○メリー, Mr.1/Mr.13）
            if len(p) >= 3:
                toks.add(p)
    return toks


@dataclass(frozen=True)
class Char:
    id: int
    name: str
    alias: str


def load_chars(path: Path) -> list[Char]:
    data = json.loads(path.read_text(encoding="utf-8"))
    out: list[Char] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        try:
            cid = int(row.get("id"))
        except Exception:
            continue
        name = str(row.get("name") or "").strip()
        if not name:
            continue
        alias = str(row.get("alias") or "").strip()
        out.append(Char(id=cid, name=name, alias=alias))
    return out


def pair_key(a: int, b: int) -> tuple[int, int]:
    return (a, b) if a < b else (b, a)


def add_pair(
    out: list[list[str]],
    seen: set[tuple[int, int, str]],
    c1: Char,
    c2: Char,
    kind: str,
    reason: str,
) -> None:
    if c1.id == c2.id:
        return
    k = pair_key(c1.id, c2.id)
    sig = (k[0], k[1], kind)
    if sig in seen:
        return
    seen.add(sig)
    out.append([kind, str(k[0]), c1.name if c1.id == k[0] else c2.name, str(k[1]), c2.name if c2.id == k[1] else c1.name, reason])


def knowledge_equivalence_sets() -> list[tuple[str, list[str]]]:
    """
    ワンピース知識ベース（最小限）。
    - ここで挙げた名前/別名が characters.json に存在すれば、その組み合わせを「知識による一致」として出す
    """
    return [
        ("本名とコードネーム", ["ギャルディーノ", "Mr.3"]),
        ("本名とコードネーム", ["ベンサム", "Mr.2", "ボン・クレー"]),
        ("本名とコードネーム", ["ダズ・ボーネス", "Mr.1"]),
        ("本名とコードネーム", ["ジェム", "Mr.5"]),
        ("本名とコードネーム", ["マリアンヌ", "ミス・ゴールデンウィーク"]),
        ("本名とコードネーム", ["ニコ・ロビン", "ミス・オールサンデー"]),
        ("変名/仮の姿", ["モンキー・D・ルフィ", "ルーシー"]),
        ("変名/仮の姿", ["ウソップ", "そげキング"]),
        ("表記ゆれ/異名", ["エドワード・ニューゲート", "白ひげ"]),
        ("表記ゆれ/異名", ["シャーロット・リンリン", "ビッグ・マム"]),
        ("表記ゆれ/異名", ["カイドウ", "百獣のカイドウ"]),
    ]


def build_name_index(chars: list[Char]) -> dict[str, list[Char]]:
    mp: dict[str, list[Char]] = {}
    for c in chars:
        for cand in extract_aliases_from_name(c.name) + ([c.alias] if c.alias else []):
            k = norm_key(cand)
            if not k:
                continue
            mp.setdefault(k, []).append(c)
        # 称号 prefix を落としたキーでも入れておく
        k2 = norm_key(strip_title_like_prefixes(c.name))
        if k2:
            mp.setdefault(k2, []).append(c)
    return mp


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--master", default="src/data/characters.json")
    ap.add_argument("--output", default="duplicate_check_list.csv")
    ap.add_argument("--max_partial_per_token", type=int, default=120, help="部分一致での候補過多を抑制する上限")
    args = ap.parse_args()

    master_path = Path(args.master)
    out_path = Path(args.output)

    chars = load_chars(master_path)
    # id で安定ソート
    chars.sort(key=lambda c: c.id)

    idx = build_name_index(chars)

    out_rows: list[list[str]] = []
    seen: set[tuple[int, int, str]] = set()

    # 1) 完全一致（name が完全に同じ）
    name_to_chars: dict[str, list[Char]] = {}
    for c in chars:
        name_to_chars.setdefault(nfkc(c.name), []).append(c)
    for nm, arr in name_to_chars.items():
        if len(arr) <= 1:
            continue
        for i in range(len(arr)):
            for j in range(i + 1, len(arr)):
                add_pair(out_rows, seen, arr[i], arr[j], "完全一致", "nameが完全に同一")

    # 2) 知識による一致（固定セット）
    for label, names in knowledge_equivalence_sets():
        present: list[Char] = []
        for n in names:
            k = norm_key(n)
            present.extend(idx.get(k, []))
        # unique chars
        uniq = []
        seen_ids = set()
        for c in present:
            if c.id in seen_ids:
                continue
            seen_ids.add(c.id)
            uniq.append(c)
        if len(uniq) <= 1:
            continue
        for i in range(len(uniq)):
            for j in range(i + 1, len(uniq)):
                add_pair(out_rows, seen, uniq[i], uniq[j], "知識による一致", label)

    # 3) 部分一致（正規化キーで包含）
    #    1299件の全組み合わせは重いので、トークン→候補リストで絞る。
    token_to_chars: dict[str, list[Char]] = {}
    for c in chars:
        for t in tokens_for_partial(c.name):
            token_to_chars.setdefault(t, []).append(c)

    for c in chars:
        ck = norm_key(c.name)
        if not ck:
            continue
        # 候補収集
        candidates: set[int] = set()
        for t in tokens_for_partial(c.name):
            arr = token_to_chars.get(t, [])
            if len(arr) > args.max_partial_per_token:
                continue
            for other in arr:
                if other.id != c.id:
                    candidates.add(other.id)
        # 判定
        for oid in sorted(candidates):
            o = next((x for x in chars if x.id == oid), None)
            if o is None:
                continue
            ok = norm_key(o.name)
            if not ok:
                continue
            if ck == ok:
                continue  # 完全一致は別枠
            # Mr.1 と Mr.13 のような「番号コードネーム」の部分一致誤爆を避ける
            if is_numbered_code_name_like(ck) and is_numbered_code_name_like(ok):
                continue
            if ck in ok or ok in ck:
                add_pair(out_rows, seen, c, o, "部分一致", "正規化名で包含（片方が片方を含む）")

    # utf-8-sig
    with out_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["判定内容", "キャラ1(ID)", "キャラ1名前", "キャラ2(ID)", "キャラ2名前", "理由"])
        w.writerows(out_rows)

    print(f"Wrote {out_path} ({len(out_rows)} pairs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

