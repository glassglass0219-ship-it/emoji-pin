import os
import requests
from bs4 import BeautifulSoup
import json
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MASTER_JSON = os.path.join(BASE_DIR, "src", "data", "volumes_master.json")

# ブラウザになりすます設定
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "ja,en-US;q=0.9,en;q=0.8"
}

def get_best_asin(query):
    """指定された正解ワードで検索し、一番上のASINを抜き出す"""
    url = f"https://www.amazon.co.jp/s?k={requests.utils.quote(query)}&i=digital-text"
    try:
        time.sleep(3) # Amazonを怒らせないための休憩
        r = requests.get(url, headers=HEADERS, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        # 検索結果の1番目の要素を探す
        result = soup.find("div", {"data-asin": True})
        if result and result["data-asin"]:
            return result["data-asin"]
    except: pass
    return None

def rebuild_master():
    # 既存のデータを読み込み（なければ空から）
    master = {}
    if os.path.exists(MASTER_JSON):
        with open(MASTER_JSON, 'r', encoding='utf-8') as f:
            master = json.load(f)

    # 1巻から111巻までを正確なワードでスキャン
    for vol in range(1, 112):
        v_str = str(vol)
        if v_str not in master: master[v_str] = {"mono": None, "color": None}

        # モノクロ版のASINをあなたの「正解ワード」で取得
        if not master[v_str].get("mono"):
            print(f"📖 {vol}巻 モノクロ版をスキャン中...")
            asin = get_best_asin(f"ONE PIECE 第{vol}巻 モノクロ版")
            if asin:
                master[v_str]["mono"] = asin
                print(f"  ✅ 発見: {asin}")

        # カラー版のASINを取得
        if not master[v_str].get("color"):
            print(f"🎨 {vol}巻 カラー版をスキャン中...")
            asin = get_best_asin(f"ONE PIECE カラー版 第{vol}巻")
            if asin:
                master[v_str]["color"] = asin
                print(f"  ✅ 発見: {asin}")

        # 都度保存
        with open(MASTER_JSON, 'w', encoding='utf-8') as f:
            json.dump(master, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    rebuild_master()