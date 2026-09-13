import httpx
import re

url = "https://www.bing.com/search?q=discord+open+dm+with+user+id+link+url"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
r = httpx.get(url, headers=headers)
snippets = re.findall(r'<div class="b_caption"><p>(.*?)</p>', r.text)
for s in snippets[:6]:
    print("-", re.sub(r'<[^>]+>', '', s))
