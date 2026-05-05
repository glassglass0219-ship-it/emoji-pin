#!/usr/bin/env python3
"""
characters / skills / locations に en_name、manga_anime_map に en_title を付与する。

- 日本語 Wiki API: langlinks (lllang=en) をバッチで試行（設定されている項目のみヒット）。
- 章ページ: ja の「第N話」記事が無いため、英語 Wiki の正規ページ名 Chapter N を en_title とする。
- 補完: 上記で空のキャラ・地名・技は Wikidata (wbsearchentities) で
  description に "one piece" を含む候補の英語ラベルを採用する。
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "src" / "data"

JA_API = "https://onepiece.fandom.com/ja/api.php"
EN_API = "https://onepiece.fandom.com/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"

BATCH_SIZE = 25
SLEEP_S = 0.3
RETRIES = 4

CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(
        {
            "User-Agent": CHROME_UA,
            "Accept": "application/json",
        }
    )
    return s


def _resolve_canonical(title: str, redirect_map: dict[str, str]) -> str:
    seen: set[str] = set()
    t = title
    while t in redirect_map and t not in seen:
        seen.add(t)
        t = redirect_map[t]
    return t


def fetch_ja_langlinks_batch(
    session: requests.Session, titles: list[str]
) -> dict[str, str]:
    """日本語ページ名 -> 英語 interlanguage リンク先タイトル（あれば）。"""
    if not titles:
        return {}
    data = {
        "action": "query",
        "format": "json",
        "titles": "|".join(titles),
        "prop": "langlinks",
        "lllang": "en",
        "redirects": "1",
    }
    payload = _post_with_retry(session, JA_API, data)
    redirect_map: dict[str, str] = {}
    for rd in payload.get("query", {}).get("redirects") or []:
        fr, to = rd.get("from"), rd.get("to")
        if isinstance(fr, str) and isinstance(to, str):
            redirect_map[fr] = to

    canon_to_en: dict[str, str] = {}
    for page in payload.get("query", {}).get("pages", {}).values():
        if page.get("missing"):
            continue
        ja = page.get("title")
        if not isinstance(ja, str):
            continue
        for ll in page.get("langlinks") or []:
            if ll.get("lang") == "en":
                star = ll.get("*")
                if isinstance(star, str) and star:
                    canon_to_en[ja] = star
                break

    out: dict[str, str] = {}
    for req in titles:
        canon = _resolve_canonical(req, redirect_map)
        en = canon_to_en.get(canon, "")
        if en:
            out[req] = en
    return out


def fetch_en_chapter_titles_batch(
    session: requests.Session, chapter_nums: list[int]
) -> dict[int, str]:
    """Chapter N の英語 Wiki 正規ページ名（存在しない話は省略）。"""
    if not chapter_nums:
        return {}
    titles = [f"Chapter {n}" for n in chapter_nums]
    data = {
        "action": "query",
        "format": "json",
        "titles": "|".join(titles),
        "redirects": "1",
    }
    payload = _post_with_retry(session, EN_API, data)
    out: dict[int, str] = {}
    re_ch = re.compile(r"^Chapter (\d+)$")
    for page in payload.get("query", {}).get("pages", {}).values():
        if page.get("missing"):
            continue
        t = page.get("title")
        if not isinstance(t, str):
            continue
        m = re_ch.match(t.strip())
        if m:
            out[int(m.group(1))] = t
    return out


def _post_with_retry(session: requests.Session, url: str, data: dict) -> dict:
    last_exc: Exception | None = None
    for attempt in range(RETRIES):
        try:
            r = session.post(url, data=data, timeout=60)
            if r.status_code == 403:
                time.sleep(1.0 + attempt)
                continue
            r.raise_for_status()
            return r.json()
        except (requests.RequestException, ValueError, json.JSONDecodeError) as e:
            last_exc = e
            time.sleep(0.8 * (attempt + 1))
    raise RuntimeError(f"API failed: {url} {last_exc}") from last_exc


def wikidata_onepiece_en_label(session: requests.Session, query: str, lang: str) -> str:
    """One Piece 関連エンティティの英語ラベルを返す（無ければ空）。"""
    time.sleep(SLEEP_S)
    try:
        r = session.get(
            WIKIDATA_API,
            params={
                "action": "wbsearchentities",
                "search": query,
                "language": lang,
                "limit": "12",
                "format": "json",
            },
            timeout=45,
        )
        r.raise_for_status()
        payload = r.json()
    except (requests.RequestException, ValueError, json.JSONDecodeError):
        return ""

    for hit in payload.get("search") or []:
        desc = (
            (hit.get("display") or {}).get("description", {}).get("value")
            or hit.get("description")
            or ""
        )
        if "one piece" not in desc.lower():
            continue
        disp_lab = (hit.get("display") or {}).get("label") or {}
        if isinstance(disp_lab, dict):
            val = disp_lab.get("value")
            if isinstance(val, str) and val.strip():
                return val.strip()
        lab = hit.get("label")
        if isinstance(lab, str) and lab.strip():
            return lab.strip()
    return ""


def batched_ja_langlinks(session: requests.Session, titles: list[str]) -> dict[str, str]:
    merged: dict[str, str] = {}
    for i in range(0, len(titles), BATCH_SIZE):
        chunk = titles[i : i + BATCH_SIZE]
        merged.update(fetch_ja_langlinks_batch(session, chunk))
        time.sleep(SLEEP_S)
    return merged


def batched_en_chapters(session: requests.Session, nums: list[int]) -> dict[int, str]:
    merged: dict[int, str] = {}
    for i in range(0, len(nums), BATCH_SIZE):
        chunk = nums[i : i + BATCH_SIZE]
        merged.update(fetch_en_chapter_titles_batch(session, chunk))
        time.sleep(SLEEP_S)
    return merged


def ensure_character_fields(chars: list[dict]) -> None:
    for c in chars:
        if isinstance(c, dict) and "en_name" not in c:
            c["en_name"] = ""


def ensure_skill_fields(skills: list[dict]) -> None:
    for s in skills:
        if isinstance(s, dict) and "en_name" not in s:
            s["en_name"] = ""


def ensure_location_fields(locs: list[dict]) -> None:
    for loc in locs:
        if isinstance(loc, dict) and "en_name" not in loc:
            loc["en_name"] = ""


def ensure_map_fields(manga_map: dict) -> None:
    for _k, v in manga_map.items():
        if isinstance(v, dict) and "en_title" not in v:
            v["en_title"] = ""


def main() -> None:
    session = make_session()

    char_path = DATA / "characters.json"
    skills_path = DATA / "skills.json"
    loc_path = DATA / "locations.json"
    map_path = DATA / "manga_anime_map.json"

    with char_path.open(encoding="utf-8") as f:
        chars: list[dict] = json.load(f)
    with skills_path.open(encoding="utf-8") as f:
        skills: list[dict] = json.load(f)
    with loc_path.open(encoding="utf-8") as f:
        locs: list[dict] = json.load(f)
    with map_path.open(encoding="utf-8") as f:
        manga_map: dict = json.load(f)

    ensure_character_fields(chars)
    ensure_skill_fields(skills)
    ensure_location_fields(locs)
    ensure_map_fields(manga_map)

    stats = {
        "chapters_en": 0,
        "chapters_total": len(manga_map),
        "characters_ja": 0,
        "characters_wd": 0,
        "characters_total": len(chars),
        "locations_ja": 0,
        "locations_wd": 0,
        "locations_total": len(locs),
        "skills_ja": 0,
        "skills_wd": 0,
        "skills_total": len(skills),
    }

    print("1/4 Chapter en_title via EN Wiki (Chapter N)...", flush=True)
    chap_nums = sorted(int(k) for k in manga_map.keys())
    chap_lookup = batched_en_chapters(session, chap_nums)
    for k in manga_map:
        n = int(k)
        en = chap_lookup.get(n, "")
        if en:
            manga_map[k]["en_title"] = en
            stats["chapters_en"] += 1

    print("2/4 Characters: JA langlinks batch...", flush=True)
    char_names = sorted({str(c.get("name", "")).strip() for c in chars if c.get("name")})
    char_ja = batched_ja_langlinks(session, char_names)
    for c in chars:
        nm = str(c.get("name", "")).strip()
        en = char_ja.get(nm, "")
        if en:
            c["en_name"] = en
            stats["characters_ja"] += 1

    print("   Characters: Wikidata fallback (One Piece)...", flush=True)
    wd_seen: dict[str, str] = {}
    for c in chars:
        if str(c.get("en_name", "")).strip():
            continue
        nm = str(c.get("name", "")).strip()
        if not nm:
            continue
        if nm in wd_seen:
            en = wd_seen[nm]
        else:
            en = wikidata_onepiece_en_label(session, nm, "ja")
            wd_seen[nm] = en
        if en:
            c["en_name"] = en
            stats["characters_wd"] += 1

    print("3/4 Locations: JA langlinks batch...", flush=True)
    loc_names = sorted({str(loc.get("name", "")).strip() for loc in locs if loc.get("name")})
    loc_ja = batched_ja_langlinks(session, loc_names)
    for loc in locs:
        nm = str(loc.get("name", "")).strip()
        en = loc_ja.get(nm, "")
        if en:
            loc["en_name"] = en
            stats["locations_ja"] += 1

    print("   Locations: Wikidata fallback...", flush=True)
    wd_loc: dict[str, str] = {}
    for loc in locs:
        if str(loc.get("en_name", "")).strip():
            continue
        nm = str(loc.get("name", "")).strip()
        if not nm:
            continue
        if nm in wd_loc:
            en = wd_loc[nm]
        else:
            en = wikidata_onepiece_en_label(session, nm, "ja")
            wd_loc[nm] = en
        if en:
            loc["en_name"] = en
            stats["locations_wd"] += 1

    print("4/4 Skills: JA langlinks + Wikidata (low hit expected)...", flush=True)
    skill_names = sorted({str(s.get("name", "")).strip() for s in skills if s.get("name")})
    skill_ja = batched_ja_langlinks(session, skill_names)
    for s in skills:
        nm = str(s.get("name", "")).strip()
        en = skill_ja.get(nm, "")
        if en:
            s["en_name"] = en
            stats["skills_ja"] += 1

    wd_skill: dict[str, str] = {}
    for sk in skills:
        if str(sk.get("en_name", "")).strip():
            continue
        nm = str(sk.get("name", "")).strip()
        if not nm:
            continue
        if nm in wd_skill:
            en = wd_skill[nm]
        else:
            en = wikidata_onepiece_en_label(session, nm, "ja")
            wd_skill[nm] = en
        if en:
            sk["en_name"] = en
            stats["skills_wd"] += 1

    def dump_json(path: Path, obj: object) -> None:
        with path.open("w", encoding="utf-8", newline="\n") as f:
            json.dump(obj, f, ensure_ascii=False, indent=2)
            f.write("\n")

    dump_json(char_path, chars)
    dump_json(skills_path, skills)
    dump_json(loc_path, locs)
    dump_json(map_path, manga_map)

    ch_filled = stats["chapters_en"]
    c_filled = stats["characters_ja"] + stats["characters_wd"]
    l_filled = stats["locations_ja"] + stats["locations_wd"]
    s_filled = stats["skills_ja"] + stats["skills_wd"]

    print("\n========== Report ==========", flush=True)
    print(
        f"manga_anime_map.json  en_title: {ch_filled} / {stats['chapters_total']} "
        f"(EN Wiki 「Chapter N」正規名)",
        flush=True,
    )
    print(
        f"characters.json       en_name:  {c_filled} / {stats['characters_total']} "
        f"(JA langlinks {stats['characters_ja']}, Wikidata {stats['characters_wd']})",
        flush=True,
    )
    print(
        f"locations.json        en_name:  {l_filled} / {stats['locations_total']} "
        f"(JA langlinks {stats['locations_ja']}, Wikidata {stats['locations_wd']})",
        flush=True,
    )
    print(
        f"skills.json           en_name:  {s_filled} / {stats['skills_total']} "
        f"(JA langlinks {stats['skills_ja']}, Wikidata {stats['skills_wd']})",
        flush=True,
    )
    print("\nSaved:", char_path, skills_path, loc_path, map_path, sep="\n  ", flush=True)


if __name__ == "__main__":
    os.chdir(ROOT)
    main()
