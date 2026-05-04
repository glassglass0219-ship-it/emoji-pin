import requests

h = {"User-Agent": "Mozilla/5.0"}
j = requests.get(
    "https://onepiece.fandom.com/api.php",
    params={
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "titles": "Chapter 1",
        "format": "json",
    },
    headers=h,
    timeout=30,
).json()
wt = list(j["query"]["pages"].values())[0]["revisions"][0]["slots"]["main"]["*"]
open("_ch1_full.wiki", "w", encoding="utf-8").write(wt)
