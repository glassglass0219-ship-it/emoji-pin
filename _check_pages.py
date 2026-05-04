import requests

h = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}
for page in ["East_Blue_Saga/Episode_Guide", "Episode Guide/East Blue Saga"]:
    p = {"action": "parse", "page": page, "format": "json", "prop": "text"}
    j = requests.get("https://onepiece.fandom.com/api.php", params=p, headers=h, timeout=20).json()
    if "error" in j:
        print(page, "ERR", j["error"].get("info"))
    else:
        html = j["parse"]["text"]["*"]
        print(page, "OK", len(html))
