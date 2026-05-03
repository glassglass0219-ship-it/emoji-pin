"""
1〜114巻の単行本表紙画像を Fandom Wiki の File:Volume_N.png から取得し、
public/images/covers/ に N.png で保存する（既存ファイルはスキップ）。

  pip install requests
  python cover_downloader.py
"""

from __future__ import annotations

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
    os.makedirs(SAVE_DIR, exist_ok=True)
    session = requests.Session()
    session.headers.update(HEADERS)

    print("全巻の表紙画像をダウンロード開始します…")
    print("※111巻以降など、まだ発売されていない巻はスキップされます。")

    downloaded = 0
    skipped_existing = 0
    failed = 0

    for i in range(1, 115):
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
