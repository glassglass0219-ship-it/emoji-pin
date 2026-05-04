import requests

p = {"action": "parse", "page": "Episode 1", "format": "json", "prop": "text"}
html = requests.get("https://onepiece.fandom.com/api.php", params=p, timeout=20).json()[
    "parse"
]["text"]["*"]
for key in ["Chapters", "Chapter", "Screenplay"]:
    i = html.find(key)
    print(key, i)
i = html.find("data-source")
while True:
    j = html.find("Chapters", i)
    if j == -1:
        break
    print("Chapters at", j)
    print(html[j - 80 : j + 400])
    i = j + 1
    break
