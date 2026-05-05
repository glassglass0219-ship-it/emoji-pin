#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
from pathlib import Path

import requests
from PIL import Image

import sync_images as si


def download_to_webp_q80(session: requests.Session, url: str, out_path: Path) -> None:
    r = session.get(url, timeout=90)
    r.raise_for_status()
    im = Image.open(io.BytesIO(r.content))
    im = im.convert("RGBA")
    im = im.resize((400, 400), Image.Resampling.LANCZOS)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    im.save(out_path, format="WEBP", quality=80, method=6)


def main() -> int:
    ap = argparse.ArgumentParser(description="指定IDに手動でサムネを設定（400x400 WebP）")
    ap.add_argument("--thumb-dir", default="public/images/thumbnails")
    args = ap.parse_args()

    thumb_dir = Path(args.thumb_dir)

    targets = [
        (278, "トラファルガー・ロー", "https://onepiecewt100-2026.com/assets/faces/0512.png?v=gjdgxu"),
        (531, "チャオ", "https://onepiecewt100-2026.com/assets/faces/0880.png?v=gjdgxu"),
        (642, "ビール", "https://onepiecewt100-2026.com/assets/faces/1083.png?v=gjdgxu"),
        (687, "ロックス・D・ジーベック", "https://onepiecewt100-2026.com/assets/faces/1543.png?v=gjdgxu"),
        (781, "ズニーシャ", "https://onepiecewt100-2026.com/assets/faces/0908.png?v=gjdgxu"),
        (831, "針神", "https://onepiecewt100-2026.com/assets/faces/1500.png?v=gjdgxu"),
        (873, "ドラウグル", "https://onepiecewt100-2026.com/assets/faces/1531.png?v=gjdgxu"),
        (874, "フェンリル", "https://onepiecewt100-2026.com/assets/faces/1529.png?v=gjdgxu"),
        (895, "マックスマークス", "https://onepiecewt100-2026.com/assets/faces/1319.png?v=gjdgxu"),
    ]

    session = requests.Session()
    session.headers.update({"User-Agent": si.CHROME_UA})

    downloaded = 0
    skipped = 0
    failed = 0

    for cid, name, url in targets:
        out_p = thumb_dir / f"{cid}.webp"
        if out_p.exists():
            skipped += 1
            continue
        try:
            si.remove_stale_images(cid)
            download_to_webp_q80(session, url, out_p)
            downloaded += 1
            print(f"[OK] {cid} {name}")
        except Exception as e:
            failed += 1
            print(f"[FAIL] {cid} {name}: {repr(e)[:160]}")

    print()
    print(f"downloaded: {downloaded}")
    print(f"skipped(existing): {skipped}")
    print(f"failed: {failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

