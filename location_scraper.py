"""
ONE PIECE 地名（国・島・施設など）と初登場漫画話数を Fandom Wiki から取得し、
src/data/locations.json に保存する。

1) MediaWiki API `list=categorymembers` で Category:Locations を起点に
   サブカテゴリを BFS で辿り、名前空間 0 の全ページタイトルを収集。
2) 各ページは `action=parse` + `prop=text` で HTML を取得し、
   Portable Infobox の `jname` / `first` を優先。旧式 infobox テーブルはフォールバック。
3) `first` 欄から正規表現で最初の「Chapter N」の N を chapter とする。

  pip install requests beautifulsoup4
  python location_scraper.py
  python location_scraper.py --limit 50   # デバッグ用
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import re
import sys
import time
from collections import deque

import requests
from bs4 import BeautifulSoup
from requests.exceptions import ChunkedEncodingError, ConnectionError as RequestsConnectionError
from urllib3.exceptions import ProtocolError

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

API_URL = "https://onepiece.fandom.com/api.php"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "src", "data", "locations.json")
ROOT_CATEGORY = "Category:Locations"

# Fandom 前面のボット判定を避けるため、anime_map_scraper と同系のブラウザ風 UA を使う
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

RE_CHAPTER = re.compile(r"Chapter\s+(\d+)", re.IGNORECASE)
# 一覧・メタページは地名ではないため除外
SKIP_TITLE_PREFIXES = (
    "List of ",
)

REQUEST_TIMEOUT = 35
PARALLEL = 3
RETRIES = 6
PARSE_PAUSE_S = 0.22


def api_get_json(session: requests.Session, params: dict) -> dict | None:
    merged = {"format": "json", **params}
    for attempt in range(RETRIES):
        try:
            r = session.get(API_URL, params=merged, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            if r.status_code != 200:
                time.sleep(min(5.0, 0.4 * (2**attempt)))
                continue
            if not r.text.strip().startswith("{"):
                time.sleep(min(5.0, 0.4 * (2**attempt)))
                continue
            return r.json()
        except (RequestsConnectionError, ProtocolError, ChunkedEncodingError, OSError, ValueError):
            time.sleep(min(5.0, 0.4 * (2**attempt)))
    return None


def iter_category_members(session: requests.Session, cmtitle: str):
    """1 カテゴリの全メンバー（ページ・サブカテゴリ）を yield（ページネーション対応）。"""
    cont: dict = {}
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": cmtitle,
            "cmlimit": "max",
            "cmnamespace": "0|14",
        }
        params.update(cont)
        data = api_get_json(session, params)
        if not data or "query" not in data:
            break
        for m in data["query"].get("categorymembers", []):
            yield m
        cont = data.get("continue") or {}
        if not cont:
            break


def collect_all_page_titles(session: requests.Session) -> list[str]:
    queue: deque[str] = deque([ROOT_CATEGORY])
    seen_cats: set[str] = set()
    pages: set[str] = set()

    while queue:
        cat = queue.popleft()
        if cat in seen_cats:
            continue
        seen_cats.add(cat)
        print(f"  [cat] {cat} …")
        n_sub = 0
        n_page = 0
        for m in iter_category_members(session, cat):
            ns = m["ns"]
            title = m["title"]
            if ns == 14:
                n_sub += 1
                if title not in seen_cats:
                    queue.append(title)
            elif ns == 0:
                if any(title.startswith(p) for p in SKIP_TITLE_PREFIXES):
                    continue
                pages.add(title)
                n_page += 1
        print(f"       → +{n_page} pages, +{n_sub} subcats queued")

    return sorted(pages)


def first_chapter_number(text: str) -> int | None:
    if not text:
        return None
    m = RE_CHAPTER.search(text)
    return int(m.group(1)) if m else None


def extract_from_portable_infobox(soup: BeautifulSoup) -> tuple[str, str] | None:
    """Portable Infobox から (japanese_name, first_field_raw) を返す。"""
    aside = soup.select_one("aside.portable-infobox")
    if not aside:
        return None

    def cell(source: str) -> str:
        node = aside.select_one(f'div.pi-data[data-source="{source}"] .pi-data-value')
        return node.get_text(" ", strip=True) if node else ""

    jname = cell("jname")
    first = cell("first") or cell("debut")
    if not first:
        return None
    return (jname, first)


def extract_from_legacy_table(soup: BeautifulSoup) -> tuple[str, str] | None:
    """旧式テーブル: Japanese Name / First appearance 行を探す。"""
    jname = ""
    first_raw = ""
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all(["th", "td"])
            if len(cells) < 2:
                continue
            label = cells[0].get_text(" ", strip=True).lower().rstrip(":")
            val = cells[1].get_text(" ", strip=True)
            if "japanese name" in label:
                jname = val
            if "first appearance" in label:
                first_raw = val
        if first_raw:
            break
    if not first_raw:
        return None
    return (jname, first_raw)


def parse_location_page(session: requests.Session, page: str) -> dict | None:
    params = {
        "action": "parse",
        "page": page,
        "prop": "text",
        "redirects": 1,
    }
    data = None
    for _ in range(3):
        data = api_get_json(session, params)
        if data and "error" not in data and "parse" in data:
            break
        time.sleep(0.8 + PARSE_PAUSE_S)
    if not data or "error" in data or "parse" not in data:
        return None
    html = data["parse"]["text"]["*"]
    title = data["parse"].get("title") or page
    soup = BeautifulSoup(html, "html.parser")

    jname = ""
    first_raw = ""

    pi = extract_from_portable_infobox(soup)
    if pi:
        jname, first_raw = pi
    else:
        leg = extract_from_legacy_table(soup)
        if leg:
            jname, first_raw = leg

    ch = first_chapter_number(first_raw)
    if ch is None:
        return None

    jn = jname.strip()
    if jn.upper() in ("N/A", "N/A.", "—", "-", "?"):
        jn = ""

    return {
        "name": title.strip(),
        "japaneseName": jn,
        "chapter": ch,
    }


def scrape_locations(limit: int | None = None) -> list[dict]:
    session = requests.Session()
    session.headers.update(HEADERS)

    print("カテゴリ Category:Locations（およびサブカテゴリ）からページ一覧を収集…")
    titles = collect_all_page_titles(session)
    print(f"収集ページ数: {len(titles)}")
    if limit is not None:
        titles = titles[:limit]
        print(f"--limit により {limit} 件に制限して取得します。")

    by_title: dict[str, dict] = {}
    errors = 0

    def work(title: str) -> tuple[str, dict | None]:
        local = requests.Session()
        local.headers.update(HEADERS)
        time.sleep(PARSE_PAUSE_S)
        row = parse_location_page(local, title)
        return title, row

    print(f"各ページを parse 取得（workers={PARALLEL}）…")
    with concurrent.futures.ThreadPoolExecutor(max_workers=PARALLEL) as pool:
        futs = {pool.submit(work, t): t for t in titles}
        done = 0
        for fut in concurrent.futures.as_completed(futs):
            title = futs[fut]
            done += 1
            try:
                req, row = fut.result()
            except Exception:
                errors += 1
                row = None
            else:
                if row:
                    by_title[req] = row
            if done % 80 == 0 or done == len(titles):
                print(f"  進捗 {done}/{len(titles)} … 有効 {len(by_title)} 件, 例外 {errors}")
            if not row and done <= 5:
                # 先頭数件の欠損は表示（デバッグ）
                pass

    missing = [t for t in titles if t not in by_title]
    if missing:
        print(f"欠損 {len(missing)} 件を順次リトライ（API負荷緩和）…")
        for i, t in enumerate(missing, start=1):
            time.sleep(0.5)
            row = parse_location_page(session, t)
            if row:
                by_title[t] = row
            if i % 30 == 0 or i == len(missing):
                print(f"  リトライ {i}/{len(missing)} … 累計 {len(by_title)} 件")

    results = list(by_title.values())
    results.sort(key=lambda r: (r["chapter"], r["name"].lower()))
    return results


def main() -> None:
    ap = argparse.ArgumentParser(description="Fandom Locations → locations.json")
    ap.add_argument("--limit", type=int, default=None, help="処理するページ数の上限（試験用）")
    args = ap.parse_args()

    rows = scrape_locations(limit=args.limit)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    print(f"\n完了。{len(rows)} 件を {OUTPUT_PATH} に保存しました。")


if __name__ == "__main__":
    main()
