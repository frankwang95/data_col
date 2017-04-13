import requests
import sys



html = sys.argv[1]
agent = sys.argv[2]
print requests.get(html, headers={'User-Agent':agent}).text.encode('utf-8')