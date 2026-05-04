import requests

h = {"User-Agent": "Mozilla/5.0"}
j = requests.get(
    "https://onepiece.fandom.com/api.php",
    params={
        "action": "query",
        "format": "json",
        "prop": "revisions",
        "rvprop": "content",
        "rvslots": "main",
        "titles": "Episode 1",
    },
    headers=h,
    timeout=30,
).json()
wt = list(j["query"]["pages"].values())[0]["revisions"][0]["slots"]["main"]["*"]
open("_ep1_head.wiki", "w", encoding="utf-8").write(wt[:3500])
