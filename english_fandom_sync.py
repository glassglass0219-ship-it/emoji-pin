#!/usr/bin/env python3
"""
英語版 One Piece Fandom の各話ページから登場キャラを取得し、
langlinks で日本語名に変換して characters.json を更新する。
langlinks に ja が無い場合は Wikidata（One Piece 関連のみ）で日本語ラベルを補完する。
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
from pathlib import Path

import requests
from bs4 import BeautifulSoup

from name_corrections_apply import apply_name_corrections

ROOT = Path(__file__).resolve().parent
EN_API = "https://onepiece.fandom.com/api.php"
JA_API = "https://onepiece.fandom.com/ja/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
CHAR_PATH = ROOT / "src" / "data" / "characters.json"
MAP_PATH = ROOT / "src" / "data" / "manga_anime_map.json"

SESSION = requests.Session()
SESSION.headers.update(
    {
        "User-Agent": "GrandlineEnglishFandomSync/1.0 (+https://onepiece.fandom.com; local data sync)",
        "Accept-Language": "en-US,en;q=0.9,ja;q=0.8",
    }
)

# 名前変換キャッシュ（API 負荷軽減）
name_map_cache: dict[str, str | None] = {}
# 日本語記事名 → リダイレクト元の別名（ja Fandom）
redirect_expand_cache: dict[str, frozenset[str]] = {}

SKIP_TITLE_PREFIXES = ("Category:", "File:", "Template:", "Help:", "User:")


def norm(s: str) -> str:
    return unicodedata.normalize("NFKC", (s or "").strip())


def expand_ja_name_variants(ja_primary: str) -> frozenset[str]:
    """ja 記事の正規名＋、その記事へ向くリダイレクト元タイトルをまとめる（サンジ vs ヴィンスモーク・サンジ等）。"""
    if ja_primary in redirect_expand_cache:
        return redirect_expand_cache[ja_primary]
    pool: set[str] = {ja_primary}
    try:
        r = SESSION.get(
            JA_API,
            params={
                "action": "query",
                "titles": ja_primary,
                "prop": "redirects",
                "format": "json",
                "rdlimit": "500",
            },
            timeout=45,
        )
        r.raise_for_status()
        for pg in r.json().get("query", {}).get("pages", {}).values():
            for rd in pg.get("redirects") or []:
                t = (rd.get("title") or "").strip()
                if t:
                    pool.add(t)
    except (requests.RequestException, KeyError, ValueError, json.JSONDecodeError):
        pass
    out = frozenset(pool)
    redirect_expand_cache[ja_primary] = out
    return out


def find_character(chars: list[dict], ja_primary: str) -> dict | None:
    norms = {norm(x) for x in expand_ja_name_variants(ja_primary) if x}
    for c in chars:
        if norm(c.get("name", "")) in norms:
            return c
        al = str(c.get("alias") or "").strip()
        if not al:
            continue
        if norm(al) in norms:
            return c
        for part in re.split(r"[,、／/]", al):
            p = part.strip()
            if p and norm(p) in norms:
                return c
    return None


def strip_disambiguation_suffix(title: str) -> str:
    """末尾の (broadcast) / (silhouette) 等を段階的に取り除く。"""
    t = title.strip()
    for _ in range(4):
        n = re.sub(r"\s*\([^)]*\)\s*$", "", t).strip()
        if n == t:
            break
        t = n
    return t


def get_japanese_name_fandom(en_title: str) -> str | None:
    params = {
        "action": "query",
        "titles": en_title,
        "prop": "langlinks",
        "lllang": "ja",
        "format": "json",
        "redirects": "1",
    }
    r = SESSION.get(EN_API, params=params, timeout=45)
    r.raise_for_status()
    data = r.json()
    pages = data.get("query", {}).get("pages", {})
    for pg in pages.values():
        if pg.get("missing"):
            continue
        links = pg.get("langlinks") or []
        if links:
            return links[0]["*"]
    return None


def get_japanese_name_wikidata(en_title: str) -> str | None:
    """description に One Piece を含むエントリのみ採用。"""
    for search_title in (en_title, strip_disambiguation_suffix(en_title)):
        if not search_title:
            continue
        r = SESSION.get(
            WIKIDATA_API,
            params={
                "action": "wbsearchentities",
                "search": search_title,
                "language": "en",
                "limit": 12,
                "format": "json",
            },
            timeout=45,
        )
        r.raise_for_status()
        data = r.json()
        for it in data.get("search", []):
            desc = (it.get("display", {}).get("description", {}) or {}).get("value") or it.get("description") or ""
            if "one piece" not in desc.lower():
                continue
            qid = it["id"]
            r2 = SESSION.get(
                WIKIDATA_API,
                params={
                    "action": "wbgetentities",
                    "ids": qid,
                    "props": "labels",
                    "languages": "ja",
                    "format": "json",
                },
                timeout=45,
            )
            r2.raise_for_status()
            ent = r2.json().get("entities", {}).get(qid, {})
            ja = (ent.get("labels") or {}).get("ja", {}).get("value")
            if ja:
                return ja
        time.sleep(0.15)
    return None


def get_japanese_name(en_title: str) -> str | None:
    if en_title in name_map_cache:
        return name_map_cache[en_title]

    ja: str | None = None
    try:
        ja = get_japanese_name_fandom(en_title)
        if not ja:
            ja = get_japanese_name_wikidata(en_title)
    except (requests.RequestException, KeyError, ValueError, json.JSONDecodeError):
        ja = None

    name_map_cache[en_title] = ja
    return ja


def extract_character_en_titles(html: str) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    anchor = soup.find(id="Characters")
    if anchor is None:
        return []

    h = anchor.find_parent(["h2", "h3"])
    if h is None:
        return []

    table = h.find_next_sibling("table")
    if table is None or "CharTable" not in (table.get("class") or []):
        return []

    titles: list[str] = []
    seen: set[str] = set()
    for a in table.select("li > a[href^='/wiki/']"):
        t = (a.get("title") or "").strip()
        if not t or t in seen:
            continue
        if any(t.startswith(p) for p in SKIP_TITLE_PREFIXES):
            continue
        seen.add(t)
        titles.append(t)
    return titles


def sort_appearances(chars: list[dict]) -> None:
    for c in chars:
        apps = c.get("appearances")
        if isinstance(apps, list):
            apps.sort(key=lambda x: int(x.get("episode", 0)) if str(x.get("episode", "")).isdigit() else 0)


def new_character_stub(char_id: int, ja_name: str, ep: int, ep_title: str) -> dict:
    return {
        "id": char_id,
        "name": ja_name,
        "reading": "",
        "gender": "",
        "affiliation": "",
        "devilFruit": "",
        "bounty": "",
        "birthday": "",
        "firstAppearance": ep,
        "appearances": [{"episode": ep, "title": ep_title}],
    }


def sync_from_english_wiki() -> list[str]:
    with CHAR_PATH.open(encoding="utf-8") as f:
        chars: list[dict] = json.load(f)
    with MAP_PATH.open(encoding="utf-8") as f:
        manga_map: dict = json.load(f)

    next_id = max(int(c["id"]) for c in chars) + 1
    start_ep, end_ep = 1115, 1181
    new_names: list[str] = []

    for ep in range(start_ep, end_ep + 1):
        print(f"解析中: Chapter {ep}...")
        params = {
            "action": "parse",
            "page": f"Chapter_{ep}",
            "format": "json",
            "prop": "text",
            "redirects": "1",
        }
        try:
            r = SESSION.get(EN_API, params=params, timeout=60)
            r.raise_for_status()
            payload = r.json()
        except (requests.RequestException, json.JSONDecodeError) as e:
            print(f"  (スキップ: 取得失敗 {e})")
            time.sleep(0.3)
            continue

        if "error" in payload:
            print(f"  (スキップ: {payload.get('error', {}).get('info', 'error')})")
            time.sleep(0.3)
            continue

        html = payload["parse"]["text"]["*"]
        en_titles = extract_character_en_titles(html)
        ep_title = (manga_map.get(str(ep)) or {}).get("title") or "Unknown"

        for en_name in en_titles:
            ja_name = get_japanese_name(en_name)
            if not ja_name:
                continue

            target = find_character(chars, ja_name)
            if target is not None:
                apps = target.setdefault("appearances", [])
                if not isinstance(apps, list):
                    continue
                if not any(
                    isinstance(a, dict) and int(a.get("episode", -1)) == ep
                    for a in apps
                ):
                    apps.append({"episode": ep, "title": ep_title})
            else:
                print(f"  [NEW] 新キャラ: {ja_name}")
                new_names.append(ja_name)
                chars.append(new_character_stub(next_id, ja_name, ep, ep_title))
                next_id += 1

        time.sleep(0.3)

    sort_appearances(chars)
    apply_name_corrections(chars)

    with CHAR_PATH.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)
        f.write("\n")

    print(f"完了。最新 ID は {next_id - 1} です。")
    if new_names:
        print(f"新規追加 {len(new_names)} 名: {', '.join(new_names)}")
    else:
        print("新規追加キャラはありませんでした。")
    return new_names


if __name__ == "__main__":
    sync_from_english_wiki()
