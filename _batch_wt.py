import requests

h = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}
titles = "|".join(f"Episode {i}" for i in range(1, 11))
p = {
    "action": "query",
    "format": "json",
    "prop": "revisions",
    "rvprop": "content",
    "rvslots": "main",
    "titles": titles,
}
j = requests.get("https://onepiece.fandom.com/api.php", params=p, headers=h, timeout=40).json()
for pid, page in j["query"]["pages"].items():
    if int(pid) < 0:
        print("missing", page)
        continue
    title = page["title"]
    wt = page["revisions"][0]["slots"]["main"]["*"]
    i = wt.lower().find("chapter")
    print(title, "chapter idx", i, "snippet", wt[i : i + 120].replace("\n", " ") if i >= 0 else "")
