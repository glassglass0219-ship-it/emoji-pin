"""
ONE PIECE Database Scraper
==========================
onepiecedb.web.fc2.com からキャラクター情報・技・登場話数を取得し、
JSONファイルとして出力するスクリプト。

使い方:
  pip install requests beautifulsoup4
  python scraper.py

出力:
  src/data/characters.json
  src/data/skills.json
  src/data/last_updated.json
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import os
import re
from datetime import datetime
import sys
from urllib.parse import quote_plus
import hashlib
import hmac
from datetime import timezone

BASE_URL = "http://onepiecedb.web.fc2.com"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "src", "data")
DELAY = 1.5  # サイトへの負荷軽減（秒）

HEADERS = {
    "User-Agent": "OnePieceDB-GrandLine-App/1.0 (Personal Study Use)"
}

# 各巻の開始話数（1〜114巻）
VOLUME_STARTS = [
    1, 9, 18, 27, 36, 45, 54, 63, 72, 82, 91, 100, 109, 118, 127, 137, 146, 156, 167, 177,
    187, 196, 206, 217, 227, 237, 247, 257, 265, 276, 286, 296, 306, 317, 328, 337, 347, 358, 368, 378,
    389, 400, 410, 420, 431, 441, 451, 460, 471, 482, 492, 503, 513, 523, 533, 542, 552, 563, 574, 585,
    595, 604, 615, 626, 637, 647, 657, 668, 679, 689, 701, 711, 722, 732, 743, 753, 764, 776, 786, 796,
    807, 817, 828, 839, 849, 859, 870, 880, 890, 901, 911, 922, 932, 943, 954, 965, 975, 985, 995, 1005,
    1016, 1026, 1036, 1047, 1058, 1069, 1081, 1091, 1101, 1111, 1122, 1134, 1145, 1156,
]


def get_volume_from_episode(episode):
    """話数から巻数を計算（VOLUME_STARTS による正確マッピング）"""
    if not episode:
        return 1
    try:
        ep = int(str(episode))
    except Exception:
        return 1
    if ep <= 0:
        return 1
    if ep >= VOLUME_STARTS[-1]:
        return len(VOLUME_STARTS)
    for i in range(len(VOLUME_STARTS) - 1, -1, -1):
        if ep >= VOLUME_STARTS[i]:
            return i + 1
    return 1


def fetch_page(url):
    """ページを取得してBeautifulSoupオブジェクトを返す"""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.encoding = resp.apparent_encoding
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"  ⚠ 取得失敗: {url} - {e}")
        return None


def fetch_amazon_asin(volume_no):
    """
    Amazon Product Advertising API (PA-API) で Kindle版のASINを取得する。

    必要な環境変数:
      - AMAZON_PAAPI_ACCESS_KEY
      - AMAZON_PAAPI_SECRET_KEY
      - AMAZON_PAAPI_PARTNER_TAG   (例: yourtag-22)

    注意:
      PA-API 5.0 は 2026-04-30 で終了アナウンスがあります（利用可否はアカウント/時期次第）。
      失敗した場合は asins.json を手動追記してください。
    """

    access_key = os.getenv("AMAZON_PAAPI_ACCESS_KEY", "").strip()
    secret_key = os.getenv("AMAZON_PAAPI_SECRET_KEY", "").strip()
    partner_tag = os.getenv("AMAZON_PAAPI_PARTNER_TAG", "").strip()

    if not access_key or not secret_key or not partner_tag:
        raise RuntimeError("PA-API環境変数が未設定です（AMAZON_PAAPI_ACCESS_KEY/SECRET_KEY/PARTNER_TAG）")

    host = "webservices.amazon.co.jp"
    region = "us-west-2"
    service = "ProductAdvertisingAPIv1"
    endpoint = f"https://{host}/paapi5/searchitems"
    target = "com.amazon.paapi5.v1.ProductAdvertisingAPIv1.SearchItems"

    keywords = f"ONE PIECE {volume_no} Kindle版"
    payload = {
        "Keywords": keywords,
        "SearchIndex": "KindleStore",
        "ItemCount": 1,
        "PartnerTag": partner_tag,
        "PartnerType": "Associates",
        "Resources": [],
    }

    data = paapi_signed_post(
        endpoint=endpoint,
        host=host,
        region=region,
        service=service,
        target=target,
        access_key=access_key,
        secret_key=secret_key,
        payload=payload,
    )

    # レスポンス構造は環境差があり得るため、複数パターンでASINを拾う
    candidates = []
    try:
        candidates.append(data.get("SearchResult", {}).get("Items", [])[0].get("ASIN"))
    except Exception:
        pass
    try:
        candidates.append(data.get("ItemsResult", {}).get("Items", [])[0].get("ASIN"))
    except Exception:
        pass
    try:
        candidates.append(data.get("SearchResult", {}).get("Items", [])[0].get("ASIN"))
    except Exception:
        pass

    asin = next((c for c in candidates if c), None)
    if not asin:
        raise RuntimeError(f"ASIN取得失敗: volume={volume_no}, response_keys={list(data.keys())}")
    return asin


def _sign(key, msg):
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _get_signature_key(key, date_stamp, region_name, service_name):
    k_date = _sign(("AWS4" + key).encode("utf-8"), date_stamp)
    k_region = hmac.new(k_date, region_name.encode("utf-8"), hashlib.sha256).digest()
    k_service = hmac.new(k_region, service_name.encode("utf-8"), hashlib.sha256).digest()
    k_signing = hmac.new(k_service, "aws4_request".encode("utf-8"), hashlib.sha256).digest()
    return k_signing


def paapi_signed_post(*, endpoint, host, region, service, target, access_key, secret_key, payload):
    """
    PA-API 5.0 の SigV4 署名付きPOSTを行い、JSONを返す。
    """
    t = datetime.now(timezone.utc)
    amz_date = t.strftime("%Y%m%dT%H%M%SZ")
    date_stamp = t.strftime("%Y%m%d")

    method = "POST"
    canonical_uri = "/paapi5/searchitems"
    canonical_querystring = ""

    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    payload_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()

    canonical_headers = (
        f"content-encoding:amz-1.0\n"
        f"content-type:application/json; charset=utf-8\n"
        f"host:{host}\n"
        f"x-amz-date:{amz_date}\n"
        f"x-amz-target:{target}\n"
    )
    signed_headers = "content-encoding;content-type;host;x-amz-date;x-amz-target"

    canonical_request = (
        f"{method}\n{canonical_uri}\n{canonical_querystring}\n"
        f"{canonical_headers}\n{signed_headers}\n{payload_hash}"
    )

    algorithm = "AWS4-HMAC-SHA256"
    credential_scope = f"{date_stamp}/{region}/{service}/aws4_request"
    string_to_sign = (
        f"{algorithm}\n{amz_date}\n{credential_scope}\n"
        f"{hashlib.sha256(canonical_request.encode('utf-8')).hexdigest()}"
    )

    signing_key = _get_signature_key(secret_key, date_stamp, region, service)
    signature = hmac.new(signing_key, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

    authorization_header = (
        f"{algorithm} Credential={access_key}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )

    headers = {
        "content-encoding": "amz-1.0",
        "content-type": "application/json; charset=utf-8",
        "host": host,
        "x-amz-date": amz_date,
        "x-amz-target": target,
        "Authorization": authorization_header,
        "User-Agent": HEADERS["User-Agent"],
    }

    resp = requests.post(endpoint, data=payload_json.encode("utf-8"), headers=headers, timeout=20)
    # エラー時は詳細を出しやすく
    try:
        data = resp.json()
    except Exception:
        raise RuntimeError(f"PA-API response not JSON: status={resp.status_code}, text={resp.text[:400]}")

    if resp.status_code >= 400:
        raise RuntimeError(f"PA-API error: status={resp.status_code}, body={data}")

    return data


def update_asins_json(latest_volume=114, *, fetch_missing=False, delay_seconds=4.0):
    """
    src/data/asins.json を差分更新する。

    - fetch_missing=False: 未登録巻を表示して保存（手動追記向け）
    - fetch_missing=True : PA-APIで未登録巻を順次取得して追記（負荷軽減のため長めディレイ）
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    asins_path = os.path.join(OUTPUT_DIR, "asins.json")
    existing = {}
    if os.path.exists(asins_path):
        with open(asins_path, "r", encoding="utf-8") as f:
            existing = json.load(f) or {}

    missing = [v for v in range(1, latest_volume + 1) if str(v) not in existing]
    print(f"asins.json 既存: {len(existing)}巻 / 未登録: {len(missing)}巻")
    if missing:
        print("未登録の巻:", ", ".join(map(str, missing[:30])) + (" ..." if len(missing) > 30 else ""))

    if fetch_missing and missing:
        for v in missing:
            if str(v) in existing:
                continue
            try:
                asin = fetch_amazon_asin(v)
                existing[str(v)] = asin
                print(f"  ✅ vol {v}: {asin}")
            except Exception as e:
                print(f"  ⚠ vol {v}: 取得失敗 - {e}")
            time.sleep(delay_seconds)

    with open(asins_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)

    print(f"保存先: {asins_path}")


def get_character_list():
    """キャラクター一覧ページから全キャラのID・名前・URLを取得"""
    print("📋 キャラクター一覧を取得中...")
    soup = fetch_page(f"{BASE_URL}/personae/list.html")
    if not soup:
        return []

    characters = []
    table = soup.find("table")
    if not table:
        return []

    for row in table.find_all("tr")[1:]:  # ヘッダ行をスキップ
        cols = row.find_all("td")
        if len(cols) >= 2:
            link = cols[0].find("a")
            if link:
                href = link.get("href", "")
                # URLからIDを抽出 (例: /personae/2.html -> 2)
                match = re.search(r"/personae/(\d+)\.html", href)
                if match:
                    char_id = int(match.group(1))
                    name = link.get_text(strip=True)
                    reading = cols[1].get_text(strip=True) if len(cols) > 1 else ""
                    characters.append({
                        "id": char_id,
                        "name": name,
                        "reading": reading,
                        "url": href if href.startswith("http") else f"{BASE_URL}/personae/{char_id}.html"
                    })

    print(f"  ✅ {len(characters)}人のキャラクターを検出")
    return characters


def get_character_detail(char_info):
    """個別キャラクターページから詳細情報を取得"""
    url = char_info["url"]
    soup = fetch_page(url)
    if not soup:
        return None

    detail = {
        "id": char_info["id"],
        "name": char_info["name"],
        "reading": char_info["reading"],
        "gender": "",
        "affiliation": "",
        "devilFruit": "",
        "bounty": "",
        "birthday": "",
        "firstAppearance": "",
        "appearances": [],
        "abilities": [],
        "coAppearances": [],
    }

    # === 基本情報テーブル ===
    tables = soup.find_all("table")
    for table in tables:
        rows = table.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) == 2:
                key = cols[0].get_text(strip=True)
                val = cols[1].get_text(strip=True)
                if key == "性別":
                    detail["gender"] = val
                elif key == "所属組織":
                    detail["affiliation"] = val
                elif key == "悪魔の実":
                    detail["devilFruit"] = val
                elif key == "最新の懸賞金":
                    detail["bounty"] = val
                elif key == "誕生日":
                    detail["birthday"] = val

    # === 初登場回 ===
    headings = soup.find_all(["h3", "h4"])
    for heading in headings:
        text = heading.get_text(strip=True)

        if "初登場回" in text:
            next_el = heading.find_next("ul")
            if next_el:
                first_link = next_el.find("a")
                if first_link:
                    ep_text = first_link.get_text(strip=True)
                    ep_match = re.match(r"(\d+)話", ep_text)
                    if ep_match:
                        detail["firstAppearance"] = int(ep_match.group(1))

        # === 技一覧 ===
        if "技" in text and "個" in text:
            next_table = heading.find_next("table")
            if next_table:
                for row in next_table.find_all("tr")[1:]:
                    cols = row.find_all("td")
                    if len(cols) >= 2:
                        skill_link = cols[0].find("a")
                        if skill_link:
                            skill_name = skill_link.get_text(strip=True)
                            skill_href = skill_link.get("href", "")
                            skill_id_match = re.search(r"/skill/(\d+)\.html", skill_href)
                            skill_reading = cols[1].get_text(strip=True) if len(cols) > 1 else ""
                            # reading列にもリンクがある場合
                            reading_link = cols[1].find("a") if len(cols) > 1 else None
                            if reading_link:
                                skill_reading = reading_link.get_text(strip=True)

                            detail["abilities"].append({
                                "id": int(skill_id_match.group(1)) if skill_id_match else 0,
                                "name": skill_name,
                                "reading": skill_reading,
                            })

        # === 共演キャラ ===
        if "同じ話に登場したキャラクター" in text:
            next_table = heading.find_next("table")
            if next_table:
                for row in next_table.find_all("tr")[1:]:
                    cols = row.find_all("td")
                    if len(cols) >= 3:
                        co_link = cols[1].find("a")
                        if co_link:
                            co_name = co_link.get_text(strip=True)
                            co_href = co_link.get("href", "")
                            co_id_match = re.search(r"/personae/(\d+)\.html", co_href)
                            count_text = cols[2].get_text(strip=True)
                            detail["coAppearances"].append({
                                "id": int(co_id_match.group(1)) if co_id_match else 0,
                                "name": co_name,
                                "count": int(count_text) if count_text.isdigit() else 0,
                            })

    # === 登場話リスト ===
    for heading in headings:
        text = heading.get_text(strip=True)
        if "登場する話" in text:
            next_ul = heading.find_next("ul")
            if next_ul:
                for li in next_ul.find_all("li"):
                    link = li.find("a")
                    if link:
                        ep_text = link.get_text(strip=True)
                        ep_match = re.match(r"(\d+)話\s*(.*)", ep_text)
                        if ep_match:
                            ep_num = int(ep_match.group(1))
                            detail["appearances"].append({
                                "episode": ep_num,
                                "title": ep_match.group(2).strip(),
                                "volume": get_volume_from_episode(ep_num),
                            })

    return detail


def get_skill_detail(skill_id):
    """技の詳細ページから登場話数などを取得"""
    url = f"{BASE_URL}/skill/{skill_id}.html"
    soup = fetch_page(url)
    if not soup:
        return None

    detail = {
        "id": skill_id,
        "name": "",
        "reading": "",
        "description": "",
        "users": [],
        "episodes": [],
    }

    # 技名
    h2 = soup.find("h2")
    if h2:
        detail["name"] = h2.get_text(strip=True)

    headings = soup.find_all(["h3", "h4"])
    for heading in headings:
        text = heading.get_text(strip=True)

        if "読み方" in text:
            next_p = heading.find_next(["p", "div"])
            if next_p:
                detail["reading"] = next_p.get_text(strip=True)

        if "説明" in text:
            next_ul = heading.find_next("ul")
            if next_ul:
                descriptions = []
                for li in next_ul.find_all("li"):
                    descriptions.append(li.get_text(strip=True))
                detail["description"] = "。".join(descriptions)

        if "使うキャラクター" in text:
            next_ul = heading.find_next("ul")
            if next_ul:
                for li in next_ul.find_all("li"):
                    link = li.find("a")
                    if link:
                        user_name = link.get_text(strip=True)
                        user_href = link.get("href", "")
                        user_id_match = re.search(r"/personae/(\d+)\.html", user_href)
                        detail["users"].append({
                            "id": int(user_id_match.group(1)) if user_id_match else 0,
                            "name": user_name,
                        })

        # 登場話（"登場する話" / "登場話数" などに対応）
        if ("登場" in text) and ("話" in text):
            # 見出し直後の <ul> を優先して探す（find_next で取りこぼすケース対策）
            next_ul = None
            for sib in heading.next_siblings:
                # 改行などのテキストノードはスキップ
                if getattr(sib, "name", None) is None:
                    continue
                if sib.name == "ul":
                    next_ul = sib
                    break
                # 次の見出しに到達したら打ち切り
                if sib.name in ("h3", "h4"):
                    break
            if next_ul is None:
                next_ul = heading.find_next("ul")

            if next_ul:
                for li in next_ul.find_all("li"):
                    link = li.find("a")
                    if not link:
                        continue
                    ep_text = link.get_text(strip=True)
                    ep_match = re.match(r"(\d+)話\s?(.*)", ep_text)
                    if not ep_match:
                        continue

                    title = (ep_match.group(2) or "").strip()
                    # タイトルが空でも episode が取れれば追加
                    ep_num = int(ep_match.group(1))
                    detail["episodes"].append({
                        "episode": ep_num,
                        "title": title,
                        "volume": get_volume_from_episode(ep_num),
                    })

    return detail


def run_full_scrape():
    """全データのフルスクレイピング"""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. キャラクター一覧を取得
    char_list = get_character_list()
    if not char_list:
        print("❌ キャラクター一覧の取得に失敗しました")
        return

    # 2. 各キャラクターの詳細を取得
    characters = []
    skill_ids_to_fetch = set()

    for i, char_info in enumerate(char_list):
        print(f"👤 [{i+1}/{len(char_list)}] {char_info['name']} を取得中...")
        detail = get_character_detail(char_info)
        if detail:
            characters.append(detail)
            # 技IDを収集
            for ability in detail.get("abilities", []):
                if ability.get("id"):
                    skill_ids_to_fetch.add(ability["id"])
        time.sleep(DELAY)

    # 3. 技の詳細を取得
    skills = []
    skill_ids_list = sorted(skill_ids_to_fetch)
    print(f"\n⚔️  {len(skill_ids_list)}個の技を取得中...")

    for i, skill_id in enumerate(skill_ids_list):
        print(f"  ⚔️  [{i+1}/{len(skill_ids_list)}] 技ID {skill_id} を取得中...")
        skill_detail = get_skill_detail(skill_id)
        if skill_detail:
            skills.append(skill_detail)
        time.sleep(DELAY)

    # 4. JSONとして保存
    with open(os.path.join(OUTPUT_DIR, "characters.json"), "w", encoding="utf-8") as f:
        json.dump(characters, f, ensure_ascii=False, indent=2)

    with open(os.path.join(OUTPUT_DIR, "skills.json"), "w", encoding="utf-8") as f:
        json.dump(skills, f, ensure_ascii=False, indent=2)

    meta = {
        "lastUpdated": datetime.now().isoformat(),
        "characterCount": len(characters),
        "skillCount": len(skills),
        "source": "http://onepiecedb.web.fc2.com/"
    }
    with open(os.path.join(OUTPUT_DIR, "last_updated.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 完了！")
    print(f"   キャラクター: {len(characters)}人")
    print(f"   技: {len(skills)}個")
    print(f"   保存先: {OUTPUT_DIR}")


def run_update_check():
    """
    差分チェック: 前回取得時との差分を検出して更新があったキャラだけ再取得
    """
    meta_path = os.path.join(OUTPUT_DIR, "last_updated.json")
    chars_path = os.path.join(OUTPUT_DIR, "characters.json")

    if not os.path.exists(meta_path) or not os.path.exists(chars_path):
        print("📦 初回実行のため、フルスクレイピングを実行します")
        run_full_scrape()
        return

    # 現在の一覧を取得
    current_list = get_character_list()
    if not current_list:
        print("❌ 一覧の取得に失敗")
        return

    # 既存データを読み込み
    with open(chars_path, "r", encoding="utf-8") as f:
        existing_chars = json.load(f)

    existing_ids = {c["id"] for c in existing_chars}
    current_ids = {c["id"] for c in current_list}

    # 新キャラ検出
    new_ids = current_ids - existing_ids
    if new_ids:
        print(f"🆕 {len(new_ids)}人の新キャラクターを検出！")
        new_chars_info = [c for c in current_list if c["id"] in new_ids]
        for char_info in new_chars_info:
            print(f"   👤 {char_info['name']} を取得中...")
            detail = get_character_detail(char_info)
            if detail:
                existing_chars.append(detail)
            time.sleep(DELAY)

        # 保存
        with open(chars_path, "w", encoding="utf-8") as f:
            json.dump(existing_chars, f, ensure_ascii=False, indent=2)

        meta = {
            "lastUpdated": datetime.now().isoformat(),
            "characterCount": len(existing_chars),
            "source": "http://onepiecedb.web.fc2.com/"
        }
        with open(os.path.join(OUTPUT_DIR, "last_updated.json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        print(f"✅ 更新完了: {len(new_ids)}人追加")
    else:
        print("✅ 新しいキャラクターはありませんでした")

    # 削除されたキャラ
    removed_ids = existing_ids - current_ids
    if removed_ids:
        print(f"⚠️  {len(removed_ids)}人のキャラが一覧から消えています")


def run_skills_only():
    """
    skills.json のみ更新（技詳細ページから再取得）。
    既存の skills.json がある前提で、そこに含まれる技IDを使って再取得する。
    """
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    skills_path = os.path.join(OUTPUT_DIR, "skills.json")
    if not os.path.exists(skills_path):
        print("skills.json が見つからないため、フルスクレイピングを実行します")
        run_full_scrape()
        return

    with open(skills_path, "r", encoding="utf-8") as f:
        existing_skills = json.load(f)

    skill_ids_list = sorted({int(s.get("id")) for s in existing_skills if s.get("id")})
    print(f"\n⚔️  {len(skill_ids_list)}個の技を再取得して skills.json を更新します...")
    skills = []

    for i, skill_id in enumerate(skill_ids_list):
        print(f"  ⚔️  [{i+1}/{len(skill_ids_list)}] 技ID {skill_id} を取得中...")
        skill_detail = get_skill_detail(skill_id)
        if skill_detail:
            skills.append(skill_detail)
        time.sleep(DELAY)

    with open(skills_path, "w", encoding="utf-8") as f:
        json.dump(skills, f, ensure_ascii=False, indent=2)

    meta = {
        "lastUpdated": datetime.now().isoformat(),
        "skillCount": len(skills),
        "source": "http://onepiecedb.web.fc2.com/"
    }
    with open(os.path.join(OUTPUT_DIR, "last_updated.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\n✅ skills.json 更新完了: {len(skills)}個")


if __name__ == "__main__":
    # Windows(PowerShell)の既定(cp932)でも落ちないようにUTF-8へ寄せる
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    if len(sys.argv) > 1 and sys.argv[1] == "--update":
        print("差分更新モードで実行中...\n")
        run_update_check()
    elif len(sys.argv) > 1 and sys.argv[1] == "--skills-only":
        print("技のみ更新モードで実行中...\n")
        run_skills_only()
    elif len(sys.argv) > 1 and sys.argv[1] == "--asins":
        print("ASIN一覧（asins.json）更新モードで実行中...\n")
        fetch_missing = "--fetch" in sys.argv[2:]
        # Amazonへの負荷を避け、進捗を分かりやすくするため -u 推奨
        update_asins_json(latest_volume=114, fetch_missing=fetch_missing, delay_seconds=4.0)
    else:
        print("ONE PIECE Database フルスクレイピング開始\n")
        print(f"サイトへの負荷軽減のため、{DELAY}秒間隔でリクエストします")
        print(f"759キャラ × {DELAY}秒 ≒ 約{int(759 * DELAY / 60)}分かかります\n")
        run_full_scrape()