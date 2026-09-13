import urllib.request
import json
import re

# Search github code via public API or raw files
url = "https://api.github.com/search/code?q=discord.com%2Fchannels%2F%40me+in:file"
req = urllib.request.Request(url, headers={"User-Agent": "ArclentBot"})
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        print("Github code search items:", len(data.get("items", [])))
        for item in data.get("items", [])[:5]:
            print(item.get("html_url"))
except Exception as e:
    print("Error:", e)
