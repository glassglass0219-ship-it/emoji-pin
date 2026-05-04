import re
import requests

h = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0"}
for ep in [1, 2, 6, 50]:
    j = requests.get(
        "https://onepiece.fandom.com/api.php",
        params={
            "action": "query",
            "format": "json",
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "titles": f"Episode {ep}",
        },
        headers=h,
        timeout=30,
    ).json()
    wt = list(j["query"]["pages"].values())[0]["revisions"][0]["slots"]["main"]["*"]
    m = re.search(r"\|\s*Chapters\s*=", wt, re.I)
    m2 = re.search(r"\|\s*chapter\s*=", wt, re.I)
    print(ep, "Chapters=", bool(m), "chapter=", bool(m2))
    if m:
        start = m.start()
        print(wt[start : start + 200])
