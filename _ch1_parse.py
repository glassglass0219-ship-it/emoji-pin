import requests
from bs4 import BeautifulSoup

h = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}
html = requests.get(
    "https://onepiece.fandom.com/api.php",
    params={"action": "parse", "page": "Chapter 1", "format": "json", "prop": "text"},
    headers=h,
    timeout=25,
).json()["parse"]["text"]["*"]
s = BeautifulSoup(html, "html.parser")
for d in s.select("div.pi-data"):
    lab = d.find("h3", class_="pi-data-label")
    if not lab:
        continue
    t = lab.get_text(strip=True)
    if "Anime" in t or "anime" in t:
        print("data-source", d.get("data-source"))
        print("value", d.select_one(".pi-data-value").get_text("\n", strip=True)[:500])
