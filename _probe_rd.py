import json
import requests

JA = "https://onepiece.fandom.com/ja/api.php"
for t in ["ヴィンスモーク・サンジ", "サンジ"]:
    r = requests.get(
        JA,
        params={"action": "query", "titles": t, "prop": "redirects", "format": "json", "rdlimit": "max"},
        timeout=30,
    )
    print(t, json.dumps(r.json(), ensure_ascii=False)[:1200])
