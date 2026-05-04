import requests

h = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}
p = {
    "action": "query",
    "format": "json",
    "prop": "revisions",
    "rvprop": "content",
    "rvslots": "main",
    "titles": "Episode 1",
}
j = requests.get("https://onepiece.fandom.com/api.php", params=p, headers=h, timeout=30).json()
wt = list(j["query"]["pages"].values())[0]["revisions"][0]["slots"]["main"]["*"]
for line in wt.split("\n"):
    if "Chapter" in line or "chapter" in line:
        if "Infobox" in line or "chapters" in line.lower() or "Chapter" in line:
            print(line[:200])
