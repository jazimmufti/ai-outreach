import urllib.request
import re

url = "https://discord.com/assets/web.f34f869e4c648af0.js"
data = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})).read().decode('utf-8')

# Search for /users/ in regex or route matching
for m in re.finditer(r'\/users\/[a-zA-Z0-9_\-\.\:\@\$\(\)\*\+\?\|\[\]]+', data):
    print("Found regex/path:", m.group(0))

for m in re.finditer(r'openUserProfileModal|openUserProfile|UserProfileModal', data):
    start = max(0, m.start() - 100)
    end = min(len(data), m.start() + 100)
    print("context:", data[start:end])
    break
