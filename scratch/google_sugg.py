import urllib.request
import urllib.parse
import json
import re

query = "discord open dm link user id"
url = f"https://suggestqueries.google.com/complete/search?client=firefox&q={urllib.parse.quote(query)}"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
try:
    with urllib.request.urlopen(req) as resp:
        print("Suggestions:", json.loads(resp.read().decode()))
except Exception as e:
    print(e)
