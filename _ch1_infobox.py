import requests
from bs4 import BeautifulSoup

h = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}
p = {"action": "parse", "page": "Chapter 1", "format": "json", "prop": "text"}
html = requests.get("https://onepiece.fandom.com/api.php", params=p, headers=h, timeout=25).json()[
    "parse"
]["text"]["*"]
s = BeautifulSoup(html, "html.parser")
box = s.select_one(".portable-infobox")
lines = []
if box:
    for d in box.select(".pi-data"):
        lab = d.find("h3", class_="pi-data-label")
        val = d.select_one(".pi-data-value")
        if lab and val:
            lines.append(f"{lab.get_text(strip=True)}: {val.get_text(' ', strip=True)}")
open("_ch1_fields.txt", "w", encoding="utf-8").write("\n".join(lines))
