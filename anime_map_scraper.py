"""
漫画話番号 → アニメ話数 を src/data/manga_anime_map.json に書き出します（全章網羅版）。

1) MediaWiki API で各「Episode Guide / …」ページを取得し、wikitable に
   Ep / Chapter 列がある場合は読み取ります（値は後続の Chapter 補完で上書きされ得ます）。
2) 英語版 Fandom の Episode Guide 本体には漫画話列が無いことが多いため、
   Chapter N 各ページのインフォボックス（Anime 欄）から話数を取得し、
   1 話〜 CHAPTER_FETCH_UPPER までを並列取得してマップを完成させます。
   後から取得した値で上書きし、Wiki 上の章ページを優先します。

  pip install requests beautifulsoup4
  python anime_map_scraper.py
"""

from __future__ import annotations

import concurrent.futures
import json
import os
import re
import sys
import time

import requests
from bs4 import BeautifulSoup
from requests.exceptions import ChunkedEncodingError, ConnectionError as RequestsConnectionError
from urllib3.exceptions import ProtocolError

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# ONE PIECE の全サーガ（ログ用キー）
SAGAS = [
    "East_Blue_Saga",
    "Alabasta_Saga",
    "Sky_Island_Saga",
    "Water_7_Saga",
    "Thriller_Bark_Saga",
    "Summit_War_Saga",
    "Fish-Man_Island_Saga",
    "Dressrosa_Saga",
    "Four_Emperors_Saga",
    "Wano_Country_Saga",
    "Final_Saga",
]

# Fandom 実在ページ（「Saga/Episode_Guide」形式は存在しないため Episode Guide/… に対応）
SAGA_WIKI_PAGES: dict[str, list[str]] = {
    "East_Blue_Saga": ["Episode Guide/East Blue Saga"],
    "Alabasta_Saga": ["Episode Guide/Arabasta Saga"],
    "Sky_Island_Saga": ["Episode Guide/Sky Island Saga"],
    "Water_7_Saga": ["Episode Guide/Water 7 Saga"],
    "Thriller_Bark_Saga": ["Episode Guide/Thriller Bark Saga"],
    "Summit_War_Saga": ["Episode Guide/Summit War Saga"],
    "Fish-Man_Island_Saga": ["Episode Guide/Fish-Man Island Saga"],
    "Dressrosa_Saga": ["Episode Guide/Dressrosa Saga"],
    # 四皇編はホールケーキのみ（ワノ国は下の Wano_Country_Saga で取得）
    "Four_Emperors_Saga": ["Episode Guide/Whole Cake Island Saga"],
    "Wano_Country_Saga": ["Episode Guide/Wano Country Saga"],
    "Final_Saga": ["Episode Guide/Final Saga"],
}

API_URL = "https://onepiece.fandom.com/api.php"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

RE_EPISODE_IN_ANIME_CELL = re.compile(r"Episode\s+(\d+)", re.IGNORECASE)
MAX_CHAPTER = 2000
CHAPTER_FETCH_UPPER = 1280
CHAPTER_PARALLEL = 6
CHAPTER_RETRIES = 5
REQUEST_PAUSE_GUIDE_S = 0.45


def api_parse_html(session: requests.Session, page: str) -> tuple[str | None, str | None]:
    params = {
        "action": "parse",
        "page": page,
        "format": "json",
        "prop": "text",
        "redirects": 1,
    }
    try:
        r = session.get(API_URL, params=params, headers=HEADERS, timeout=30)
    except OSError as e:
        return None, str(e)
    if r.status_code != 200:
        return None, f"HTTP {r.status_code}"
    if not r.text.strip().startswith("{"):
        return None, "non-JSON response"
    data = r.json()
    if "error" in data:
        return None, data["error"].get("info", str(data["error"]))
    return data["parse"]["text"]["*"], None


def extract_from_episode_guide_tables(html: str, manga_to_anime: dict[int, int]) -> None:
    """wikitable の Ep / Chapter 列があれば取り込む（常に上書き）。"""
    soup = BeautifulSoup(html, "html.parser")
    for table in soup.find_all("table", class_="wikitable"):
        rows = table.find_all("tr")
        if not rows:
            continue
        header_cells = rows[0].find_all(["th", "td"])
        idx_anime = -1
        idx_manga = -1
        for i, cell in enumerate(header_cells):
            txt = cell.get_text(strip=True).lower()
            if txt in ("ep", "episode"):
                idx_anime = i
            elif "chapter" in txt:
                idx_manga = i
        if idx_anime == -1 or idx_manga == -1:
            continue
        for row in rows[1:]:
            cols = row.find_all(["td", "th"])
            if len(cols) <= max(idx_anime, idx_manga):
                continue
            anime_txt = cols[idx_anime].get_text(strip=True)
            anime_match = re.search(r"(\d+)", anime_txt)
            if not anime_match:
                continue
            anime_ep = int(anime_match.group(1))
            manga_txt = cols[idx_manga].get_text(strip=True)
            for ch in re.findall(r"(\d+)", manga_txt):
                ch_num = int(ch)
                if ch_num > MAX_CHAPTER:
                    continue
                manga_to_anime[ch_num] = anime_ep


def _parse_chapter_anime_ep(html: str) -> int | None:
    soup = BeautifulSoup(html, "html.parser")
    node = soup.select_one('div.pi-data[data-source="anime"] .pi-data-value')
    if not node:
        return None
    text = node.get_text(" ", strip=True)
    eps = [int(m.group(1)) for m in RE_EPISODE_IN_ANIME_CELL.finditer(text)]
    return min(eps) if eps else None


def _chapter_row(ch: int) -> tuple[int, int | None]:
    params = {"action": "parse", "page": f"Chapter {ch}", "format": "json", "prop": "text"}
    for attempt in range(CHAPTER_RETRIES):
        try:
            r = requests.get(API_URL, params=params, headers=HEADERS, timeout=35)
            if r.status_code != 200 or not r.text.strip().startswith("{"):
                time.sleep(min(6.0, 0.5 * (2**attempt)))
                continue
            data = r.json()
            if "error" in data:
                return ch, None
            ep = _parse_chapter_anime_ep(data["parse"]["text"]["*"])
            return ch, ep
        except (RequestsConnectionError, ProtocolError, ChunkedEncodingError, OSError, ValueError):
            time.sleep(min(6.0, 0.5 * (2**attempt)))
    return ch, None


def fill_all_chapters_from_wiki(manga_to_anime: dict[int, int]) -> None:
    """Chapter 1..N を並列取得し、取得できた話は常に上書きで反映。"""
    chapters = list(range(1, CHAPTER_FETCH_UPPER + 1))
    print(
        f"Chapter 1〜{CHAPTER_FETCH_UPPER} を API で取得し、"
        f"Anime 欄からマップを完成させます（workers={CHAPTER_PARALLEL}）…"
    )
    with concurrent.futures.ThreadPoolExecutor(max_workers=CHAPTER_PARALLEL) as pool:
        for ch, ep in pool.map(_chapter_row, chapters):
            if ep is not None and ch <= MAX_CHAPTER:
                manga_to_anime[ch] = ep

    still = [c for c in chapters if c not in manga_to_anime and c <= MAX_CHAPTER]
    if still:
        print(f"欠損 {len(still)} 件を低速リトライ…")
        for i, ch in enumerate(still, start=1):
            _, ep = _chapter_row(ch)
            if ep is not None:
                manga_to_anime[ch] = ep
            time.sleep(0.12)
            if i % 40 == 0:
                time.sleep(0.8)


def scrape_mapping() -> None:
    manga_to_anime: dict[int, int] = {}
    session = requests.Session()
    session.headers.update(HEADERS)

    print("最新の全エピソード情報を取得中（Episode Guide → テーブル、上書きモード）…")
    for saga in SAGAS:
        for page_title in SAGA_WIKI_PAGES.get(saga, []):
            print(f"  {saga} ← {page_title}")
            html, err = api_parse_html(session, page_title)
            if err:
                print(f"    [ERR] {err}")
                time.sleep(REQUEST_PAUSE_GUIDE_S)
                continue
            before = len(manga_to_anime)
            extract_from_episode_guide_tables(html, manga_to_anime)
            print(f"    [OK] 累計 {len(manga_to_anime)} 件（直前から +{len(manga_to_anime) - before}）")
            time.sleep(REQUEST_PAUSE_GUIDE_S)

    fill_all_chapters_from_wiki(manga_to_anime)

    output_path = "src/data/manga_anime_map.json"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    sorted_map = {str(k): {"ep": manga_to_anime[k]} for k in sorted(manga_to_anime.keys())}

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(sorted_map, f, ensure_ascii=False, indent=2)

    print(f"\n完了。{len(sorted_map)} 件を {output_path} に保存しました。")


if __name__ == "__main__":
    scrape_mapping()
