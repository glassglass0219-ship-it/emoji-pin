import json
import requests

JA_API = "https://onepiece.fandom.com/ja/api.php"


def search_ja(q):
    r = requests.get(
        JA_API,
        params={
            "action": "query",
            "list": "search",
            "srsearch": q,
            "srnamespace": 0,
            "srlimit": 5,
            "format": "json",
        },
        timeout=30,
    )
    return r.json()


for q in ["Saturn", "ジェイガルシア", "Jaygarcia Saturn", "サターン 五老星"]:
    d = search_ja(q)
    hits = d.get("query", {}).get("search", [])
    print(q, "->", [h["title"] for h in hits])
