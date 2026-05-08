import requests
from bs4 import BeautifulSoup
import time


def get_asin_list():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept-Language": "ja,jp;q=0.9",
    }

    print("--- ONE PIECE モノクロ版 ASIN抽出開始 (Amazon.co.jp) ---")
    print("※日本の検索結果を直接確認しています...")

    for vol in range(1, 11):
        query = f"ONE PIECE モノクロ版 {vol} ジャンプコミックスDIGITAL"
        url = f"https://www.amazon.co.jp/s?k={query}&i=digital-text"

        try:
            r = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            items = soup.find_all("div", {"data-asin": True})

            found = False
            for item in items:
                asin = item["data-asin"]
                if not asin:
                    continue

                title_el = item.find("h2")
                title = title_el.get_text(strip=True) if title_el else ""

                # 「カラー版」を除外し、タイトルに巻数が含まれているか厳格にチェック
                if "カラー版" not in title and str(vol) in title:
                    print(f"第{vol}巻: {asin} | タイトル: {title[:40]}...")
                    found = True
                    break

            if not found:
                print(f"第{vol}巻: ⚠ 取得失敗 (手動確認が必要です)")

        except Exception as e:
            print(f"第{vol}巻: ❌ エラーが発生しました: {e}")

        time.sleep(2)  # 負荷軽減

    print("--- 抽出終了 ---")


if __name__ == "__main__":
    get_asin_list()
