import requests
from bs4 import BeautifulSoup

API = "https://onepiece.fandom.com/api.php"
H = {"User-Agent": "Mozilla/5.0 Chrome/124 Safari/537.36"}
r = requests.get(
    API,
    params={"action": "parse", "page": "Chapter 1100", "format": "json", "prop": "text"},
    headers=H,
    timeout=30,
)
soup = BeautifulSoup(r.json()["parse"]["text"]["*"], "html.parser")
t = soup.select_one("table.CharTable")
for a in t.select('a[href^="/wiki/"]')[:30]:
    print(repr(a.get("title")), "|", repr(a.get_text(strip=True)))
