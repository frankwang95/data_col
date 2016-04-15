import requests
import unicodedata
import sys

html = sys.argv[1]
agent = sys.argv[2]
x = requests.get(html, headers = {'User-Agent': agent}).text
print(unicodedata.normalize('NFKD', x).encode('ascii', 'ignore'))
