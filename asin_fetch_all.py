#!/usr/bin/env python3
"""Fetch Kindle ASINs for ONE PIECE モノクロ版 (1-114) and カラー版 (1-106) from Amazon.co.jp.

Saves progress incrementally to src/data/kindle_asins.json so reruns can resume.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup


OUT_PATH = Path("src/data/kindle_asins.json")
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "ja,jp;q=0.9",
}

MONO_MAX = 114
COLOR_MAX = 106
SLEEP_SEC = 2.0
RETRY_SLEEP_SEC = 5.0


def _load_existing() -> dict:
    if OUT_PATH.exists():
        try:
            return json.loads(OUT_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"mono": {}, "color": {}}


def _save(data: dict) -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _search_asin(query: str, vol: int, kind_label: str, exclude_label: str) -> str | None:
    url = f"https://www.amazon.co.jp/s?k={query}&i=digital-text"
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
    except Exception as e:
        print(f"  HTTP error: {e}")
        return None
    if r.status_code != 200:
        print(f"  HTTP {r.status_code}")
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    items = soup.find_all("div", {"data-asin": True})
    vol_str = str(vol)
    for item in items:
        asin = item.get("data-asin") or ""
        if not asin:
            continue
        title_el = item.find("h2")
        title = title_el.get_text(strip=True) if title_el else ""
        if exclude_label in title:
            continue
        if kind_label not in title:
            continue
        if vol_str not in title:
            continue
        # Strict volume number boundary check (avoid "10" matching when vol=1)
        # Look for tokens like "版 N " / "N " right after kind_label
        # Cheap heuristic: ensure the token immediately following kind_label starts with vol_str
        idx = title.find(kind_label)
        if idx >= 0:
            tail = title[idx + len(kind_label):].lstrip()
            num = ""
            for ch in tail:
                if ch.isdigit():
                    num += ch
                else:
                    break
            if num and num != vol_str:
                continue
        print(f"  hit asin={asin} title={title[:60]}")
        return asin
    return None


def _fetch_with_retry(query: str, vol: int, kind_label: str, exclude_label: str) -> str | None:
    asin = _search_asin(query, vol, kind_label, exclude_label)
    if asin:
        return asin
    print("  retrying after extra delay…")
    time.sleep(RETRY_SLEEP_SEC)
    return _search_asin(query, vol, kind_label, exclude_label)


def fetch_kind(kind: str, max_vol: int, data: dict) -> None:
    bucket = data.setdefault(kind, {})
    is_color = kind == "color"
    kind_label = "カラー版" if is_color else "モノクロ版"
    exclude_label = "モノクロ版" if is_color else "カラー版"

    print(f"=== ONE PIECE {kind_label} 1-{max_vol} ===")
    for vol in range(1, max_vol + 1):
        key = str(vol)
        if bucket.get(key):
            print(f"vol {vol}: skip (cached {bucket[key]})")
            continue
        query = f"ONE PIECE {kind_label} {vol} ジャンプコミックスDIGITAL"
        print(f"vol {vol}: {query}")
        asin = _fetch_with_retry(query, vol, kind_label, exclude_label)
        if asin:
            bucket[key] = asin
        else:
            print(f"  ⚠ failed vol={vol}")
        _save(data)
        time.sleep(SLEEP_SEC)


def main() -> int:
    data = _load_existing()
    fetch_kind("mono", MONO_MAX, data)
    fetch_kind("color", COLOR_MAX, data)
    _save(data)

    print("--- summary ---")
    for kind, max_vol in (("mono", MONO_MAX), ("color", COLOR_MAX)):
        bucket = data.get(kind, {})
        missing = [str(v) for v in range(1, max_vol + 1) if str(v) not in bucket]
        print(f"{kind}: got={len(bucket)}/{max_vol} missing={missing}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
