import concurrent.futures
import requests

h = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}


def exists(ch: int) -> tuple[int, bool]:
    p = {"action": "parse", "page": f"Chapter {ch}", "format": "json", "prop": "text"}
    j = requests.get("https://onepiece.fandom.com/api.php", params=p, headers=h, timeout=20).json()
    return ch, "error" not in j


with concurrent.futures.ThreadPoolExecutor(16) as ex:
    r = list(ex.map(exists, range(1, 31)))
print(r)
