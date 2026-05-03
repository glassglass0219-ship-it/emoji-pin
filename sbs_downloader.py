"""
麦わら一味の SBS 画像を Fandom MediaWiki API から取得し、public/images/sbs に保存して
characters.json の char.sbs.images を更新する。

依存: pip install requests

使い方: python sbs_downloader.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from urllib.parse import urlparse

import requests

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_DIR = os.path.join(BASE_DIR, "public", "images", "sbs")
JSON_PATH = os.path.join(BASE_DIR, "src", "data", "characters.json")

API_URL = "https://onepiece.fandom.com/api.php"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://onepiece.fandom.com/",
}

# Wiki 上の File: ページ名（& はリテラル。%26 は API に渡さない）
SBS_CONFIG = [
    {
        "id": 2,
        "name": "ルフィ",
        "files": {
            "child": "File:Monkey D. Luffy as a Child.png",
            "future_good": "File:Luffy Age 40 & 60.png",
            "future_bad": "File:Luffy Age 40 & 60 Bad.png",
        },
    },
    {
        "id": 9,
        "name": "ゾロ",
        "files": {
            "child": "File:Roronoa Zoro as a Child.png",
            "future_good": "File:Zoro Age 40 & 60.png",
            "future_bad": "File:Zoro Age 40 & 60 Bad.png",
        },
    },
    {
        "id": 14,
        "name": "ナミ",
        "files": {
            "child": "File:Nami as a Child.png",
            "future_good": "File:Nami Age 40 and 60.png",
            "future_bad": "File:Nami Age 40 and 60 Bad.png",
        },
    },
    {
        "id": 21,
        "name": "ウソップ",
        "files": {
            "child": "File:Usopp as a Child.png",
            "future_good": "File:Usopp Age 40 and 60.png",
            "future_bad": "File:Usopp Age 40 and 60 Bad.png",
        },
    },
    {
        "id": 36,
        "name": "サンジ",
        "files": {
            "child": "File:Sanji as a Child.png",
            "future_good": "File:Sanji Age 40 and 60.png",
            "future_bad": "File:Sanji Age 40 and 60 Bad.png",
        },
    },
    {
        "id": 92,
        "name": "チョッパー",
        "files": {
            "child": "File:Tony Tony Chopper as a Child.png",
            "future_good": "File:Chopper Age 40 and 60.png",
            "future_bad": "File:Chopper Age 40 and 60 Bad.png",
        },
    },
    {
        "id": 72,
        "name": "ロビン",
        "files": {
            "child": "File:Nico Robin as a Child.png",
            "future_good": "File:Robin Age 40 and 60.png",
            "future_bad": "File:Robin Age 40 and 60 Bad.png",
        },
    },
    {
        "id": 206,
        "name": "フランキー",
        "files": {"child": "File:Franky as a Child.png"},
    },
    {
        "id": 237,
        "name": "ブルック",
        "files": {"child": "File:Brook as a Child.png"},
    },
    {
        "id": 307,
        "name": "ジンベエ",
        "files": {"child": "File:Jinbe as a Child.png"},
    },
]


def get_latest_url(file_title: str) -> str | None:
    """MediaWiki API で File: の最新フルサイズ URL を取得。"""
    params = {
        "action": "query",
        "prop": "imageinfo",
        "iiprop": "url",
        "titles": file_title,
        "format": "json",
    }
    try:
        r = requests.get(API_URL, params=params, headers=HEADERS, timeout=15)
        r.raise_for_status()
        data = r.json()
        pages = data.get("query", {}).get("pages", {})
        for pg in pages.values():
            if pg.get("missing"):
                continue
            infos = pg.get("imageinfo")
            if infos and isinstance(infos, list) and infos[0].get("url"):
                return infos[0]["url"]
    except Exception as e:
        print(f"    API error ({file_title}): {e}")
    return None


def ext_from_url(url: str) -> str:
    path = urlparse(url.split("/revision/")[0].split("?")[0]).path.lower()
    for ext in (".png", ".webp", ".jpg", ".jpeg", ".gif"):
        if path.endswith(ext):
            return ext
    return ".png"


def download(url: str, dest_path_no_ext: str) -> str | None:
    """画像を保存し、public からの相対 Web パス（/images/sbs/...）を返す。失敗時は None。"""
    try:
        clean = url.split("/revision/")[0].split("?")[0]
        ext = ext_from_url(clean)
        out_path = dest_path_no_ext + ext
        os.makedirs(os.path.dirname(out_path), exist_ok=True)

        r = requests.get(clean, headers=HEADERS, timeout=30)
        if r.status_code != 200:
            print(f"    HTTP {r.status_code} for image")
            return None
        with open(out_path, "wb") as f:
            f.write(r.content)
        rel = os.path.relpath(out_path, os.path.join(BASE_DIR, "public")).replace("\\", "/")
        return f"/{rel}"
    except Exception as e:
        print(f"    download error: {e}")
    return None


def run() -> None:
    os.makedirs(SAVE_DIR, exist_ok=True)
    print("API経由で最新の SBS 画像 URL を取得し、ダウンロードします...")

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        chars = json.load(f)

    for item in SBS_CONFIG:
        cid = item["id"]
        print(f"--- {item['name']} (id={cid})")
        img_paths: dict[str, str] = {}

        for key, file_title in item["files"].items():
            latest = get_latest_url(file_title)
            if not latest:
                print(f"    skip {key}: no URL from API")
                time.sleep(0.5)
                continue

            dest_base = os.path.join(SAVE_DIR, f"{cid}_{key}")
            path = download(latest, dest_base)
            if path:
                img_paths[key] = path
                print(f"    OK {key} -> {path}")
            else:
                print(f"    FAIL {key}")

            time.sleep(1.0)

        for c in chars:
            if c.get("id") != cid:
                continue
            c.setdefault("sbs", {})
            prev = c["sbs"].get("images")
            prev_dict = prev if isinstance(prev, dict) else {}
            c["sbs"]["images"] = {**prev_dict, **img_paths}
            break

    tmp = JSON_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)
    os.replace(tmp, JSON_PATH)
    print("完了。public/images/sbs と characters.json を確認してください。")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    run()
