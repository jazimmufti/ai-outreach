import httpx
import re

url = "https://html.duckduckgo.com/html/?q=site:reddit.com/r/discordapp+\"channels/@me\"+user+id"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
resp = httpx.get(url, headers=headers)
snippets = re.findall(r'<a class="result__snippet[^"]*"[^>]*>(.*?)</a>', resp.text)
for s in snippets[:6]:
    clean = re.sub(r'<[^>]+>', '', s)
    print("-", clean)
