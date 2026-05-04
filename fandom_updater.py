"""
1116〜1181 話を対象に、Fandom から登場履歴・話タイトル・アニメ対応を更新する。

- 日本語 Wiki（ja）に「第N話」の記事は無いため、原作の日本語サブタイトルは
  英語 Wiki「Chapter N」の Chapter Box（jname）を採用する。
- 登場キャラは英語 Wiki の CharTable（wikitext）を解析し、ja の opensearch で
  characters.json の name に対応付ける。
- manga_anime_map.json は英語章ページの Portable Infobox「Anime」欄を
  anime_map_scraper と同じ規則で読み取り、該当話数のみ上書きする。

  pip install requests beautifulsoup4
  python fandom_updater.py
  python fandom_updater.py --start 1120 --end 1181
"""

from __future__ import annotations

import argparse
import html as html_mod
import json
import os
import re
import sys
import threading
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import requests
from bs4 import BeautifulSoup
from requests.exceptions import ChunkedEncodingError, ConnectionError as RequestsConnectionError
from urllib3.exceptions import ProtocolError

from name_corrections_apply import apply_name_corrections

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.abspath(__file__))
CHAR_PATH = os.path.join(ROOT, "src", "data", "characters.json")
MAP_PATH = os.path.join(ROOT, "src", "data", "manga_anime_map.json")

JA_API = "https://onepiece.fandom.com/ja/api.php"
EN_API = "https://onepiece.fandom.com/api.php"

DEFAULT_START_EP = 1116
DEFAULT_END_EP = 1181

HEADERS = {"User-Agent": "Mozilla/5.0"}
HEADERS_JSON = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/javascript, */*; q=0.01",
}

REQUEST_TIMEOUT = 55
RETRIES = 7
SLEEP_EPISODE_S = 0.45
API_SEM = threading.Semaphore(5)
RESOLVE_WORKERS = 5

RE_CHARTABLE_BLOCK = re.compile(r'\{\|\s*class="CharTable"[\s\S]*?\n\|\}\n', re.IGNORECASE)
RE_WIKI_LINK = re.compile(r"\[\[([^|\]#]+)(?:\|[^\]]*)?\]\]")
RE_JNAME = re.compile(r"\|\s*jname\s*=\s*([^\n]*)")
RE_EPISODE_IN_ANIME_CELL = re.compile(r"Episode\s+(\d+)", re.IGNORECASE)


def _find_template_end(s: str, open_brace: int) -> int | None:
    """open_brace は「{{」の先頭インデックス。対応する「}}」の直後インデックスを返す。"""
    if open_brace + 1 >= len(s) or s[open_brace : open_brace + 2] != "{{":
        return None
    depth = 1
    i = open_brace + 2
    while i < len(s) - 1:
        if s[i : i + 2] == "{{":
            depth += 1
            i += 2
        elif s[i : i + 2] == "}}":
            depth -= 1
            i += 2
            if depth == 0:
                return i
        else:
            i += 1
    return None


def strip_wiki_markup_to_plain_title(raw: str) -> str:
    """
    {{Ruby|表記|よみ}} は表記（第1引数）へ、それ以外の {{...}} は除去。
    ネストした {{ も再帰的に処理する。
    """
    s = html_mod.unescape((raw or "").strip())

    def replace_one_template(inner: str) -> str:
        parts = [p.strip() for p in inner.split("|")]
        if not parts:
            return ""
        name = parts[0].strip()
        # {{Ruby|暴|アトラス}} / {{ruby|...}} など
        if re.match(r"(?i)ruby", name):
            for seg in parts[1:]:
                if not seg or re.match(r"(?i)(style|size|class|width|height)=", seg):
                    continue
                return strip_wiki_markup_to_plain_title(seg)
            return ""
        # {{Nihongo|...}} 等は先頭の表示用引数を優先
        if re.match(r"(?i)nihongo|nihongo2", name) and len(parts) >= 2:
            return strip_wiki_markup_to_plain_title(parts[1])
        # その他テンプレは中身を捨てる（ノイズ除去）
        return ""

    while "{{" in s:
        start = s.find("{{")
        end = _find_template_end(s, start)
        if end is None:
            s = s.replace("{{", "", 1)
            continue
        inner = s[start + 2 : end - 2]
        repl = replace_one_template(inner)
        s = s[:start] + repl + s[end:]

    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\[\[([^|\]#]+)(?:\|([^\]]+))?\]\]", lambda m: m.group(2) or m.group(1), s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def api_get_json(url: str, params: dict) -> dict | None:
    merged = {"format": "json", **params}
    for attempt in range(RETRIES):
        for hdr in (HEADERS, HEADERS_JSON):
            try:
                with API_SEM:
                    r = requests.get(url, params=merged, headers=hdr, timeout=REQUEST_TIMEOUT)
                if r.status_code != 200:
                    continue
                t = r.text.strip()
                if not t.startswith("{"):
                    continue
                return r.json()
            except (RequestsConnectionError, ProtocolError, ChunkedEncodingError, OSError, ValueError):
                break
        time.sleep(min(5.0, 0.4 * (2**attempt)))
    return None


def portable_infobox_jname(soup: BeautifulSoup) -> str:
    aside = soup.select_one("aside.portable-infobox")
    if not aside:
        return ""
    node = aside.select_one('div.pi-data[data-source="jname"] .pi-data-value')
    if not node:
        return ""
    t = node.get_text(" ", strip=True)
    if t.upper() in ("N/A", "N/A.", "—", "-", "?", "TBA"):
        return ""
    return strip_wiki_markup_to_plain_title(t)


def parse_chapter_anime_ep_from_html(html: str) -> int | None:
    soup = BeautifulSoup(html, "html.parser")
    node = soup.select_one('div.pi-data[data-source="anime"] .pi-data-value')
    if not node:
        return None
    text = node.get_text(" ", strip=True)
    eps = [int(m.group(1)) for m in RE_EPISODE_IN_ANIME_CELL.finditer(text)]
    return min(eps) if eps else None


def chapter_jname_from_wikitext(wt: str) -> str:
    m = RE_JNAME.search(wt)
    if not m:
        return ""
    raw = html_mod.unescape(m.group(1).strip())
    return strip_wiki_markup_to_plain_title(raw)


def skip_char_table_link(display_title: str, href_slug: str) -> bool:
    t = html_mod.unescape(display_title or "").strip()
    slug = (href_slug or "").replace("_", " ").strip()
    base = t or slug
    low = base.lower()
    if not base:
        return True
    if base.endswith(" Pirates"):
        return True
    if base in (
        "Pirate",
        "Pirates",
        "World Government",
        "Marines",
        "Navy",
        "Navigation",
        "One Piece Wiki",
        "One Piece",
        "SBS",
        "Cover Page",
    ):
        return True
    if low.startswith("list of "):
        return True
    return False


def extract_chartable_en_titles_from_wikitext(wt: str) -> list[str]:
    m = RE_CHARTABLE_BLOCK.search(wt)
    if not m:
        return []
    block = m.group(0)
    seen: set[str] = set()
    out: list[str] = []
    for raw in RE_WIKI_LINK.findall(block):
        page_title = html_mod.unescape(str(raw).strip())
        if not page_title:
            continue
        if page_title.startswith(("File:", "Category:", "Image:", "Media:", "Template:")):
            continue
        disp = page_title.replace("_", " ")
        if skip_char_table_link(disp, page_title.replace(" ", "_")):
            continue
        if page_title not in seen:
            seen.add(page_title)
            out.append(page_title)
    return out


def pick_json_name_from_ja_strings(
    strings: list[str], names_by_len: list[str], names_set: set[str]
) -> str | None:
    for s in strings:
        s = (s or "").strip()
        if s in names_set:
            return s
    for s in strings:
        s = (s or "").strip()
        if not s:
            continue
        best: str | None = None
        for n in names_by_len:
            if n and n in s:
                if best is None or len(n) > len(best):
                    best = n
        if best:
            return best
    return None


def ja_opensearch_suggestions(query: str) -> list[str]:
    data = api_get_json(JA_API, {"action": "opensearch", "search": query, "limit": 12})
    if not data or len(data) < 2 or not isinstance(data[1], list):
        return []
    return [str(x) for x in data[1]]


def fetch_en_character_jname(en_page_title: str) -> str:
    data = api_get_json(
        EN_API,
        {"action": "parse", "page": en_page_title, "prop": "text", "redirects": 1},
    )
    if not data or "error" in data or "parse" not in data:
        return ""
    soup = BeautifulSoup(data["parse"]["text"]["*"], "html.parser")
    return portable_infobox_jname(soup)


def resolve_en_to_json_name(
    en_page_title: str,
    names_by_len: list[str],
    names_set: set[str],
    cache: dict[str, str],
    lock: threading.Lock,
) -> str | None:
    key = en_page_title.strip()
    if not key:
        return None
    with lock:
        if key in cache:
            return cache[key]
    cands = ja_opensearch_suggestions(key)
    jp = pick_json_name_from_ja_strings(cands, names_by_len, names_set)
    if jp:
        with lock:
            cache[key] = jp
        return jp
    jn = fetch_en_character_jname(key)
    if jn:
        jp2 = pick_json_name_from_ja_strings([jn], names_by_len, names_set)
        if jp2:
            with lock:
                cache[key] = jp2
            return jp2
    return None


def try_ja_manga_episode(ep: int) -> tuple[str | None, str | None]:
    """第N話 が存在すれば（稀）、HTML から『…』タイトルと本文テキストを返す。"""
    data = api_get_json(
        JA_API,
        {"action": "parse", "page": f"第{ep}話", "prop": "text", "redirects": 1},
    )
    if not data or "error" in data or "parse" not in data:
        return None, None
    h = data["parse"]["text"]["*"]
    m = re.search(r"「([^」]+)」", h)
    if not m:
        m = re.search(r"『([^』]+)』", h)
    title = m.group(1).strip() if m else None
    soup = BeautifulSoup(h, "html.parser")
    text_content = soup.get_text()
    return title, text_content


def fetch_en_chapter_bundle(ep: int) -> tuple[str, str, str, list[str]]:
    """
    Returns (jname_title, wikitext, html_for_anime, chartable_en_titles).
    空応答が続く場合はリトライする。
    """
    page = f"Chapter {ep}"
    wt = ""
    html = ""
    jn = ""
    titles: list[str] = []

    for attempt in range(10):
        wt_data = api_get_json(
            EN_API,
            {"action": "parse", "page": page, "prop": "wikitext", "redirects": 1},
        )
        if wt_data and "parse" in wt_data and "error" not in wt_data:
            wt = wt_data["parse"].get("wikitext", {}).get("*", "") or ""
        ht_data = api_get_json(
            EN_API,
            {"action": "parse", "page": page, "prop": "text", "redirects": 1},
        )
        if ht_data and "parse" in ht_data and "error" not in ht_data:
            html = ht_data["parse"]["text"]["*"] or ""

        jn = chapter_jname_from_wikitext(wt) if wt else ""
        titles = extract_chartable_en_titles_from_wikitext(wt) if wt else []
        if jn and "{{" in jn and html:
            soup = BeautifulSoup(html, "html.parser")
            j2 = portable_infobox_jname(soup)
            if j2 and "{{" not in j2:
                jn = j2
        if not jn and html:
            soup = BeautifulSoup(html, "html.parser")
            jn = portable_infobox_jname(soup) or ""
        if not titles and html:
            soup = BeautifulSoup(html, "html.parser")
            table = soup.find("table", class_="CharTable")
            if table:
                seen: set[str] = set()
                for a in table.find_all("a", href=True):
                    href = a.get("href") or ""
                    if not href.startswith("/wiki/"):
                        continue
                    slug = urllib.parse.unquote(href[len("/wiki/") :])
                    if slug.startswith(("File:", "Category:", "Template:", "Help:", "Special:")):
                        continue
                    title_attr = html_mod.unescape((a.get("title") or "").strip())
                    display = title_attr or slug.replace("_", " ")
                    if skip_char_table_link(display, slug):
                        continue
                    pt = title_attr if title_attr else slug.replace("_", " ")
                    if pt not in seen:
                        seen.add(pt)
                        titles.append(pt)
        if (jn and jn != "タイトル不明") or titles:
            break
        time.sleep(min(6.0, 0.5 * (attempt + 1)))

    if not jn:
        jn = "タイトル不明"
    return jn, wt, html, titles


def anime_from_ja_text(text: str) -> int | None:
    m = re.search(r"アニメ第?\s*(\d+)\s*話", text)
    return int(m.group(1)) if m else None


def normalize_episode_title(title: str) -> str:
    t = strip_wiki_markup_to_plain_title(title)
    t = re.sub(r"\s*\[\s*\d+\s*\]\s*$", "", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def upsert_appearance(char: dict, episode: int, title: str) -> bool:
    """同一話があればタイトル改善時のみ更新。無ければ追加。変更があれば True。"""
    title = normalize_episode_title(title)
    apps = char.setdefault("appearances", [])
    for a in apps:
        same = (isinstance(a.get("episode"), int) and a["episode"] == episode) or str(
            a.get("episode", "")
        ) == str(episode)
        if not same:
            continue
        old = str(a.get("title", "") or "").strip()
        if old in ("", "タイトル不明") and title and title != "タイトル不明":
            a["title"] = title
            return True
        if old != title and title and title != "タイトル不明":
            a["title"] = title
            return True
        return False
    apps.append({"episode": episode, "title": title or "タイトル不明"})
    return True


def update_specific_range(start_ep: int, end_ep: int) -> None:
    with open(CHAR_PATH, "r", encoding="utf-8") as f:
        chars: list[dict] = json.load(f)
    with open(MAP_PATH, "r", encoding="utf-8") as f:
        manga_map: dict[str, Any] = json.load(f)

    names_set = {str(c.get("name", "")).strip() for c in chars if c.get("name")}
    names_by_len = sorted(names_set, key=lambda s: len(s), reverse=True)
    name_to_char = {str(c["name"]).strip(): c for c in chars if c.get("name")}

    resolve_cache: dict[str, str] = {}
    resolve_lock = threading.Lock()

    print(
        f"第{start_ep}話〜第{end_ep}話を更新します（日本語サブタイトルは英語 Wiki jname を基準、Wiki 記法除去）。",
        flush=True,
    )

    for ep in range(start_ep, end_ep + 1):
        ja_title, ja_text = try_ja_manga_episode(ep)
        ep_title: str
        anime_ep: int | None = None
        resolved_jp_names: list[str] = []

        if ja_title and ja_text:
            ep_title = ja_title
            anime_ep = anime_from_ja_text(ja_text)
            ep_title = normalize_episode_title(ep_title)
            for c in chars:
                nm = str(c.get("name", "")).strip()
                if nm and nm in ja_text:
                    upsert_appearance(c, ep, ep_title)
        else:
            jn, _wt, html, en_titles = fetch_en_chapter_bundle(ep)
            ep_title = normalize_episode_title((jn or "").strip() or "タイトル不明")
            anime_ep = parse_chapter_anime_ep_from_html(html)

            en_titles = list(dict.fromkeys(en_titles))

            def resolve_one(t: str) -> str | None:
                return resolve_en_to_json_name(t, names_by_len, names_set, resolve_cache, resolve_lock)

            jp_set: set[str] = set()
            if en_titles:
                workers = min(RESOLVE_WORKERS, len(en_titles))
                with ThreadPoolExecutor(max_workers=workers) as ex:
                    futs = [ex.submit(resolve_one, t) for t in en_titles]
                    for fut in futs:
                        jp = fut.result()
                        if jp:
                            jp_set.add(jp)
            resolved_jp_names = sorted(jp_set)

            for jp in resolved_jp_names:
                ch = name_to_char.get(jp)
                if ch:
                    upsert_appearance(ch, ep, ep_title)

        if anime_ep is not None:
            manga_map[str(ep)] = {"ep": anime_ep}

        print(f"第{ep}話: {ep_title}" + (f"（アニメ {anime_ep}）" if anime_ep else ""), flush=True)
        time.sleep(SLEEP_EPISODE_S)

    for c in chars:
        if "appearances" in c and c["appearances"]:
            c["appearances"].sort(
                key=lambda x: int(x["episode"])
                if isinstance(x.get("episode"), int)
                else int(str(x.get("episode", "0")))
            )

    apply_name_corrections(chars)

    with open(CHAR_PATH, "w", encoding="utf-8") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)
    with open(MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(manga_map, f, ensure_ascii=False, indent=2)
    print("\nエピソード情報の更新が完了しました。", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--start",
        type=int,
        default=DEFAULT_START_EP,
        metavar="N",
        help=f"開始話数（既定: {DEFAULT_START_EP}）",
    )
    ap.add_argument(
        "--end",
        type=int,
        default=DEFAULT_END_EP,
        metavar="N",
        help=f"終了話数（既定: {DEFAULT_END_EP}）",
    )
    args = ap.parse_args()
    lo, hi = args.start, args.end
    if hi < lo:
        lo, hi = hi, lo
    update_specific_range(lo, hi)
