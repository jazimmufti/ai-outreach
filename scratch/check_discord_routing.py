import urllib.request
import re

url = "https://discord.com/assets/web.f34f869e4c648af0.js"
data = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})).read().decode('utf-8')

# Let's search for how Discord handles /users/:id
# e.g. location.pathname.startsWith('/users/') or routes
matches = re.findall(r'users/([0-9]{17,20}|:[a-zA-Z]+)', data)
print("users params:", set(matches))

# Search for /channels/@me
for m in re.finditer(r'channels/@me/[^"\']+', data):
    print("channels/@me path:", m.group(0))

for m in re.finditer(r'/users/:id', data):
    start = max(0, m.start() - 150)
    end = min(len(data), m.start() + 150)
    print("context of /users/:id ->", data[start:end])
    break
