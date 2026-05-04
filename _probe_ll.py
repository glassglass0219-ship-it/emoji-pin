import json
import requests

r = requests.get(
    "https://onepiece.fandom.com/api.php",
    params={
        "action": "query",
        "titles": "Jaygarcia Saturn",
        "prop": "langlinks",
        "format": "json",
        "redirects": 1,
        "lllimit": "50",
    },
    timeout=30,
)
with open("_probe_ll_out.json", "w", encoding="utf-8") as f:
    json.dump(r.json(), f, ensure_ascii=False, indent=2)
