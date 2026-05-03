"""
manga_anime_map.json から netflix_id を一度すべて削除したうえで、
アニメ第 1〜10 話のみ Fandom API（parse + externallinks、必要時は同レスポンスの HTML）から Netflix watch ID を再取得し、
該当する漫画話エントリへ netflix_id を書き戻します。

誤って混入しがちな「北斗の拳」の作品 ID（60033035）は保存しません。

  pip install requests
  python netflix_id_scraper.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import time

import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

API_URL = "https://onepiece.fandom.com/api.php"
MAP_PATH = "src/data/manga_anime_map.json"
BAD_ID = "60033035"  # 北斗の拳（誤検出時は無視）

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
}


def debug_scrape_top_10() -> None:
    if not os.path.exists(MAP_PATH):
        print("Error: manga_anime_map.json not found")
        return

    with open(MAP_PATH, "r", encoding="utf-8") as f:
        manga_map: dict = json.load(f)

    # 既存の netflix_id をすべて削除
    for info in manga_map.values():
        if isinstance(info, dict) and "netflix_id" in info:
            del info["netflix_id"]

    test_eps = range(1, 11)
    results: dict[str, str] = {}

    print("アニメ1話〜10話の Netflix ID を取得中…")

    for ep in test_eps:
        print(f"解析中: Episode {ep}…", end="\r", flush=True)
        # 英語版ウィキの標準タイトルは "Episode N"（スペース）。API はアンダースコアも解釈するが明示的に統一。
        params = {
            "action": "parse",
            "page": f"Episode {ep}",
            "prop": "externallinks|text",
            "format": "json",
            "redirects": 1,
        }
        try:
            r = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
            if r.status_code != 200 or not r.text.strip().startswith("{"):
                time.sleep(0.5)
                continue
            data = r.json()
            if "error" in data:
                time.sleep(0.5)
                continue
            parse = data.get("parse", {})
            links = parse.get("externallinks") or []
            if not isinstance(links, list):
                links = [links] if links else []

            v_id = None
            for link in links:
                if not isinstance(link, str) or "netflix.com/watch/" not in link.lower():
                    continue
                m = re.search(r"watch/(\d+)", link, re.IGNORECASE)
                if not m:
                    continue
                cand = m.group(1)
                if cand != BAD_ID:
                    v_id = cand
                    break

            if not v_id:
                html = (parse.get("text") or {}).get("*") or ""
                m = re.search(
                    r"https?://(?:www\.)?netflix\.com/watch/(\d+)", html, re.IGNORECASE
                )
                if m and m.group(1) != BAD_ID:
                    v_id = m.group(1)

            if v_id:
                results[str(ep)] = v_id
                print(f"  [ok] 第{ep}話: {v_id}")
        except (OSError, ValueError, KeyError):
            pass
        time.sleep(0.5)

    updated = 0
    for _manga_ch, info in manga_map.items():
        if not isinstance(info, dict) or info.get("ep") is None:
            continue
        anime_ep = str(int(info["ep"]))
        if anime_ep in results:
            info["netflix_id"] = results[anime_ep]
            updated += 1

    with open(MAP_PATH, "w", encoding="utf-8") as f:
        json.dump(manga_map, f, ensure_ascii=False, indent=2)

    print(f"\n完了。{updated} 件の漫画話エントリに netflix_id を紐付けました（取得できた話: {len(results)}）。")


if __name__ == "__main__":
    debug_scrape_top_10()
