"""
1〜115巻の単行本表紙画像を Fandom Wiki の File:Volume_N.png から取得し、
public/images/covers/ に N.png で保存する（既存ファイルはスキップ）。

  pip install requests
  python cover_downloader.py
  python cover_downloader.py --start 111 --end 114
"""

from __future__ import annotations

import argparse
import os
import sys
import time

import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = os.path.dirname(os.path.abspath(__file__))
API_URL = "https://onepiece.fandom.com/api.php"
SAVE_DIR = os.path.join(ROOT, "public", "images", "covers")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
}


def get_cover(session: requests.Session, vol: int) -> bool:
    out_path = os.path.join(SAVE_DIR, f"{vol}.png")
    # 既にファイルが存在する場合はスキップ（効率化）
    if os.path.isfile(out_path):
        return True

    params = {
        "action": "query",
        "prop": "imageinfo",
        "iiprop": "url",
        "titles": f"File:Volume_{vol}.png",
        "format": "json",
    }
    try:
        r = session.get(API_URL, params=params, timeout=20)
        r.raise_for_status()
        data = r.json()
        pages = data.get("query", {}).get("pages", {})
        for pg in pages.values():
            if pg.get("missing"):
                continue
            infos = pg.get("imageinfo") or []
            if not infos:
                continue
            img_url = infos[0].get("url")
            if not img_url:
                continue
            ir = session.get(img_url, timeout=60)
            ir.raise_for_status()
            with open(out_path, "wb") as f:
                f.write(ir.content)
            print(f"✅ Vol.{vol} 完了 → {out_path}")
            return True
    except Exception as e:
        print(f"❌ Vol.{vol} エラー: {e}")
    return False


def main() -> None:
    ap = argparse.ArgumentParser(description="単行本表紙を Fandom の File:Volume_N.png から取得")
    ap.add_argument("--start", type=int, default=1, help="開始巻（既定: 1）")
    ap.add_argument("--end", type=int, default=115, help="終了巻（既定: 115）")
    args = ap.parse_args()
    start = max(1, args.start)
    end = max(start, args.end)

    os.makedirs(SAVE_DIR, exist_ok=True)
    session = requests.Session()
    session.headers.update(HEADERS)

    print(f"表紙画像をダウンロードします（Vol.{start}〜{end}）…")
    print("※未発売などで Wiki に画像が無い巻はスキップされます。")

    downloaded = 0
    skipped_existing = 0
    failed = 0

    for i in range(start, end + 1):
        path = os.path.join(SAVE_DIR, f"{i}.png")
        existed = os.path.isfile(path)
        ok = get_cover(session, i)
        if existed:
            skipped_existing += 1
        elif ok:
            downloaded += 1
        else:
            failed += 1
        time.sleep(0.3)

    print(
        f"\nすべての取得作業が終了しました。"
        f"（新規取得: {downloaded}, 既存スキップ: {skipped_existing}, 未取得: {failed}）"
    )


if __name__ == "__main__":
    main()
