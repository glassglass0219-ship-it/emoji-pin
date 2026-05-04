import re
import requests
from bs4 import BeautifulSoup

h = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}
p = {"action": "parse", "page": "Episode Guide/East Blue Saga", "format": "json", "prop": "text"}
html = requests.get("https://onepiece.fandom.com/api.php", params=p, headers=h, timeout=25).json()[
    "parse"
]["text"]["*"]
s = BeautifulSoup(html, "html.parser")
a = s.find("a", href="/wiki/Episode_1")
tr = a.find_parent("tr")
open("_tr_ep1.txt", "w", encoding="utf-8").write(tr.get_text("\n", strip=True))
print("chapter links", [x["href"] for x in tr.find_all("a", href=re.compile(r"Chapter"))])
