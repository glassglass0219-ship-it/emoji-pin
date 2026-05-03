"""
Fandom（日本語）キャラページから SBS 系画像を取得し public/images/sbs に保存、
characters.json の char.sbs.images を更新する。

依存:
  pip install requests beautifulsoup4

用法:
  python scripts/sync_sbs_images.py

403 Forbidden が返る環境があります（データセンター IP のブロック等）。
そのときはブラウザで Fandom にログインした状態で Cookie をコピーし、実行前に設定してください:

  PowerShell:
    $env:FANDOM_COOKIE='cookie名=値; 別名=値'
    python scripts/sync_sbs_images.py

※ Wiki のマークアップは変わりうるため、ヒットしないキャラがあれば alt / キャプション条件を調整してください。
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from urllib.parse import quote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAVE_DIR = os.path.join(ROOT, "public", "images", "sbs")
JSON_PATH = os.path.join(ROOT, "src", "data", "characters.json")

# Fandom は簡素な UA で 403 になりやすいため、一般的なブラウザ相当に寄せる
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    "Referer": "https://onepiece.fandom.com/",
}

WIKI_BASE = "https://onepiece.fandom.com"

def parse_cookie_header(header: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in header.split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        k, v = part.split("=", 1)
        out[k.strip()] = v.strip()
    return out


STRAW_HATS = [
    {"id": 2, "name": "モンキー・D・ルフィ"},
    {"id": 9, "name": "ロロノア・ゾロ"},
    {"id": 14, "name": "ナミ"},
    {"id": 21, "name": "ウソップ"},
    {"id": 36, "name": "サンジ"},
    {"id": 92, "name": "トニートニー・チョッパー"},
    {"id": 72, "name": "ニコ・ロビン"},
    {"id": 206, "name": "フランキー"},
    {"id": 237, "name": "ブルック"},
    {"id": 307, "name": "ジンベエ"},
]


def normalize_img_url(raw: str | None) -> str | None:
    if not raw or raw.startswith("data:"):
        return None
    raw = raw.strip()
    if raw.startswith("//"):
        return "https:" + raw
    if raw.startswith("/"):
        return urljoin(WIKI_BASE, raw)
    return raw


def strip_revision(url: str) -> str:
    """Fandom の /revision/... を落としてオリジナル相当の URL に。"""
    return url.split("/revision/")[0].split("?")[0]


def guess_extension(url: str, content_type: str | None) -> str:
    path = urlparse(url).path.lower()
    for ext in (".webp", ".png", ".jpg", ".jpeg", ".gif"):
        if path.endswith(ext):
            return ext
    ct = (content_type or "").lower()
    if "png" in ct:
        return ".png"
    if "jpeg" in ct or "jpg" in ct:
        return ".jpg"
    if "webp" in ct:
        return ".webp"
    return ".png"


def download_image(session: requests.Session, url: str, dest_path_no_ext: str, referer: str) -> str | None:
    try:
        clean_url = strip_revision(url)
        resp = session.get(
            clean_url,
            timeout=20,
            headers={"Referer": referer},
        )
        if resp.status_code != 200:
            print(f"  WARN HTTP {resp.status_code}: {clean_url[:80]}...")
            return None
        ext = guess_extension(clean_url, resp.headers.get("Content-Type"))
        out_path = dest_path_no_ext + ext
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, "wb") as f:
            f.write(resp.content)
        rel = os.path.relpath(out_path, os.path.join(ROOT, "public")).replace("\\", "/")
        return f"/{rel}"
    except Exception as e:
        print(f"  WARN download failed: {e}")
    return None


def gather_img_text_bits(img: BeautifulSoup) -> str:
    """alt / data 属性 / 近傍キャプションをつなげて検索用文字列に。"""
    parts = [
        img.get("alt") or "",
        img.get("title") or "",
        img.get("data-image-name") or "",
        img.get("data-image-key") or "",
    ]
    parent = img.parent
    for _ in range(4):
        if parent is None:
            break
        if parent.name in ("figure", "div", "td", "li"):
            cap = parent.find(["figcaption", "div"], class_=re.compile(r"caption|lightbox", re.I))
            if cap:
                parts.append(cap.get_text(" ", strip=True))
        parent = getattr(parent, "parent", None)
    return " ".join(parts)


def classify_sbs_slot(alt_blob: str) -> str | None:
    """'child' | 'future_good' | 'future_bad' | None"""
    if re.search(r"幼少期|子供|童年|幼年|Childhood|child", alt_blob, re.I):
        return "child"
    if "40歳" in alt_blob or "60歳" in alt_blob:
        if "善" in alt_blob or "通常" in alt_blob or "順当" in alt_blob:
            return "future_good"
        if "何かあった" in alt_blob or "悪" in alt_blob or "ズレ" in alt_blob:
            return "future_bad"
    return None


def sync_sbs_images() -> None:
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        chars = json.load(f)

    session = requests.Session()
    session.headers.update(HEADERS)
    ck = os.environ.get("FANDOM_COOKIE", "").strip()
    if ck:
        session.cookies.update(parse_cookie_header(ck))
        print("Using FANDOM_COOKIE for session")

    for hat in STRAW_HATS:
        name = hat["name"]
        cid = hat["id"]
        wiki_path = quote(name, safe="")
        wiki_url = f"{WIKI_BASE}/ja/wiki/{wiki_path}"
        print(f"--- {name} (id={cid}): fetch {wiki_url}")

        images_found: dict[str, str] = {}
        try:
            resp = session.get(wiki_url, timeout=25)
            resp.raise_for_status()
            resp.encoding = resp.apparent_encoding
            soup = BeautifulSoup(resp.text, "html.parser")

            for img in soup.find_all("img"):
                src = normalize_img_url(img.get("data-src") or img.get("src"))
                if not src:
                    continue
                blob = gather_img_text_bits(img)
                slot = classify_sbs_slot(blob + " " + (img.get("data-image-name") or ""))
                if not slot or slot in images_found:
                    continue

                dest_base = os.path.join(SAVE_DIR, f"{cid}_{slot}")
                path = download_image(session, src, dest_base, wiki_url)
                if path:
                    images_found[slot] = path
                    print(f"    OK {slot} -> {path}")

            for c in chars:
                if c.get("id") != cid:
                    continue
                c.setdefault("sbs", {})
                prev = c["sbs"].get("images")
                prev_dict = prev if isinstance(prev, dict) else {}
                merged = {**prev_dict, **images_found}
                c["sbs"]["images"] = merged
                print(f"    JSON merged keys: {list(merged.keys())}")

        except Exception as e:
            print(f"  ERROR {name}: {e}")
            if "403" in str(e):
                print(
                    "      Hint: set env FANDOM_COOKIE from your browser "
                    "(after opening any onepiece.fandom.com page)."
                )

        time.sleep(1.2)

    tmp_path = JSON_PATH + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(chars, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, JSON_PATH)
    print(f"Wrote {JSON_PATH}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    os.makedirs(SAVE_DIR, exist_ok=True)
    sync_sbs_images()
