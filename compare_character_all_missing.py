#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OFF_PATH = ROOT / "src" / "data" / "extracted" / "character_all.json"
CHAR_PATH = ROOT / "src" / "data" / "characters.json"
OUT = ROOT / "character_all_missing_with_candidates.csv"


def clean_official_line(s: str) -> str:
    s = (s or "").strip("\ufeff").strip()
    if not s:
        return ""
    # strip leading artifacts like "10|"
    s = re.sub(r"^\s*\d+\|\s*", "", s)
    return s.strip()


def nfkc(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "").strip())


_SPACE_RE = re.compile(r"[ \t\u3000]+")


def norm_basic(s: str) -> str:
    t = nfkc(s)
    t = _SPACE_RE.sub("", t)
    t = t.lower()
    for ch in ["・", "･", '"', "'", "’", "‘", "“", "”", "〝", "〟", "「", "」", "『", "』"]:
        t = t.replace(ch, "")
    return t


def strip_paren(s: str) -> str:
    t = nfkc(s)
    out: list[str] = []
    depth = 0
    for ch in t:
        if ch in "（(":
            depth += 1
            continue
        if ch in "）)":
            if depth > 0:
                depth -= 1
            continue
        if depth == 0:
            out.append(ch)
    return "".join(out)


def norm_compact(s: str) -> str:
    t = norm_basic(s)
    t = re.sub(r"[^0-9a-z\u3040-\u30ff\u3400-\u9fff]", "", t)
    return t


def top_candidates(off_name: str, impl_rows: list[dict], k: int = 5) -> list[tuple[float, str, str]]:
    ob = norm_basic(off_name)
    oc = norm_compact(off_name)
    onp = norm_basic(strip_paren(off_name))
    scored: list[tuple[float, str, str]] = []

    for r in impl_rows:
        best = 0.0
        how = ""
        if ob and ob == r["basic"]:
            best = 1.0
            how = "norm_basic=="
        elif oc and oc == r["compact"]:
            best = 0.995
            how = "norm_compact=="
        elif onp and onp == r["noparen"]:
            best = 0.99
            how = "strip_paren+norm=="
        else:
            if ob and (ob in r["basic"] or r["basic"] in ob) and min(len(ob), len(r["basic"])) >= 4:
                best = max(best, 0.94)
                how = "substring(norm_basic)"
            s1 = SequenceMatcher(None, ob, r["basic"]).ratio() if ob and r["basic"] else 0.0
            s2 = SequenceMatcher(None, oc, r["compact"]).ratio() if oc and r["compact"] else 0.0
            s = s1 if s1 >= s2 else s2
            if s > best:
                best = s
                how = "fuzzy_basic" if s1 >= s2 else "fuzzy_compact"

        if best >= 0.86:
            scored.append((best, how, r["name"]))

    scored.sort(key=lambda x: (-x[0], x[2]))
    return scored[:k]


def main() -> int:
    official: list[str] = []
    for line in OFF_PATH.read_text(encoding="utf-8").splitlines():
        n = clean_official_line(line)
        if n:
            official.append(n)
    seen: set[str] = set()
    official_u: list[str] = []
    for n in official:
        if n not in seen:
            seen.add(n)
            official_u.append(n)

    chars = json.loads(CHAR_PATH.read_text(encoding="utf-8"))
    impl = [str(c.get("name") or "") for c in chars if isinstance(c, dict) and c.get("name")]
    impl_set = set(impl)

    impl_rows: list[dict] = []
    for nm in impl:
        impl_rows.append(
            {
                "name": nm,
                "basic": norm_basic(nm),
                "compact": norm_compact(nm),
                "noparen": norm_basic(strip_paren(nm)),
            }
        )

    missing = [n for n in official_u if n not in impl_set]

    with OUT.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "official_name",
                "candidate1",
                "score1",
                "reason1",
                "candidate2",
                "score2",
                "reason2",
                "candidate3",
                "score3",
                "reason3",
                "candidate4",
                "score4",
                "reason4",
                "candidate5",
                "score5",
                "reason5",
            ]
        )
        for off in missing:
            cands = top_candidates(off, impl_rows, 5)
            row: list[str] = [off]
            for sc, how, nm in cands:
                row += [nm, f"{sc:.3f}", how]
            while len(row) < 1 + 5 * 3:
                row += ["", "", ""]
            w.writerow(row)

    exact_present = len(official_u) - len(missing)
    print(f"official_unique={len(official_u)}")
    print(f"implemented_names={len(impl)}")
    print(f"exact_present={exact_present}")
    print(f"missing_exact={len(missing)}")
    print(f"wrote={OUT.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

