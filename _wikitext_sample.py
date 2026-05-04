import requests

h = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}
p = {
    "action": "query",
    "titles": "Episode Guide/East Blue Saga",
    "prop": "revisions",
    "rvprop": "content",
    "rvslots": "main",
    "format": "json",
}
j = requests.get("https://onepiece.fandom.com/api.php", params=p, headers=h, timeout=20).json()
pages = j["query"]["pages"]
pid = list(pages.keys())[0]
rev = pages[pid].get("revisions", [{}])[0]
wt = rev.get("slots", {}).get("main", {}).get("*", "")
open("_east_blue.wikitext", "w", encoding="utf-8").write(wt)
print("len", len(wt))
for needle in ["Chapter", "chapter", "Epi", "epi", "adapt"]:
    print(needle, wt.lower().find(needle.lower()))
