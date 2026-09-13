import httpx
import re

url = "https://html.duckduckgo.com/html/?q=site:github.com+%22discord.com/channels/@me/%22"
headers = {"User-Agent": "Mozilla/5.0"}
r = httpx.get(url, headers=headers)
snippets = re.findall(r'<a class="result__snippet[^"]*"[^>]*>(.*?)</a>', r.text)
for s in snippets[:6]:
    print("-", re.sub(r'<[^>]+>', '', s))
