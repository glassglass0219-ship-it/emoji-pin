import requests

r = requests.get(
    "https://onepiece.fandom.com/api.php",
    params={"action": "parse", "page": "Chapter_1115", "format": "json", "prop": "text", "redirects": 1},
    timeout=60,
)
html = r.json()["parse"]["text"]["*"]
i = html.find('id="Characters"')
print(html[i - 100 : i + 4000])
