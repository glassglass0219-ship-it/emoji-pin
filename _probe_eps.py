import requests
from bs4 import BeautifulSoup

for ep in [1, 2, 100, 500, 1000]:
    p = {"action": "parse", "page": f"Episode {ep}", "format": "json", "prop": "text"}
    r = requests.get("https://onepiece.fandom.com/api.php", params=p, timeout=20)
    j = r.json()
    if "error" in j:
        print(ep, "err", j["error"])
        continue
    html = j["parse"]["text"]["*"]
    s = BeautifulSoup(html, "html.parser")
    div = s.select_one('div.pi-data[data-source="chapter"] .pi-data-value')
    if not div:
        for d in s.select("div.pi-data"):
            lab = d.find("h3", class_="pi-data-label")
            if lab and "Chapters" in lab.get_text():
                div = d.select_one(".pi-data-value")
                break
    links = [a.get("href") for a in div.find_all("a")] if div else []
    print(ep, links[:8])
