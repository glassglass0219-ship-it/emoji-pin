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
for line in wt.split("\n"):
    if "Anime" in line or "anime" in line:
        if "|" in line[:2] or line.strip().startswith("|"):
            print(line[:300])
