import re
import time
import concurrent.futures
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}
API = "https://onepiece.fandom.com/api.php"
RE_EP = re.compile(r"Episode\s+(\d+)", re.I)


def anime_ep_for_chapter(ch: int) -> tuple[int, int | None]:
    p = {"action": "parse", "page": f"Chapter {ch}", "format": "json", "prop": "text"}
    try:
        j = requests.get(API, params=p, headers=HEADERS, timeout=25).json()
    except Exception:
        return ch, None
    if "error" in j:
        return ch, None
    html = j["parse"]["text"]["*"]
    s = BeautifulSoup(html, "html.parser")
    node = s.select_one('div.pi-data[data-source="anime"] .pi-data-value')
    if not node:
        return ch, None
    text = node.get_text(" ", strip=True)
    eps = [int(m.group(1)) for m in RE_EP.finditer(text)]
    if not eps:
        return ch, None
    return ch, min(eps)


def main():
    t0 = time.time()
    chs = range(1, 101)
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        results = list(ex.map(anime_ep_for_chapter, chs))
    ok = sum(1 for _, e in results if e is not None)
    print("ok", ok, "elapsed", time.time() - t0)
    print(results[:5])


if __name__ == "__main__":
    main()
