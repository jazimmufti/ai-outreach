import httpx
from bs4 import BeautifulSoup

url = "https://html.duckduckgo.com/html/?q=how+to+open+dm+with+discord+user+id+link"
headers = {"User-Agent": "Mozilla/5.0"}
r = httpx.get("https://html.duckduckgo.com/html/", params={"q": "discord open dm link user id"}, headers=headers)
print("status:", r.status_code)
soup = BeautifulSoup(r.text, "html.parser")
for a in soup.find_all("a", class_="result__snippet"):
    print("MATCH:", a.get_text())
