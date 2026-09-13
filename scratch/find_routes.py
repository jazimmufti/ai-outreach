import httpx
import re

r = httpx.get("https://discord.com/app", headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
assets = re.findall(r'src="(/assets/[a-f0-9]+\.js)"', r.text)
print(f"Found {len(assets)} assets")
for asset in assets[:5]:
    js_url = f"https://discord.com{asset}"
    js_resp = httpx.get(js_url, headers={"User-Agent": "Mozilla/5.0"})
    matches = re.findall(r'["\'](/users/[^"\']+|/channels/[^"\']+)["\']', js_resp.text)
    if matches:
        print(f"In {asset}: {set(matches)}")
