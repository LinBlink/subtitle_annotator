import requests

with open('api_key') as f:
    API_KEY = f.read()

url = "https://translation.googleapis.com/language/translate/v2"

params = {
    "q": "Hello, world!",
    "target": "zh",
    "source": "en",      # 省略則自動偵測
    "format": "text",    # 或 "html"
    "key": API_KEY,
}

response = requests.get(url, params=params)
data = response.json()
print(data["data"]["translations"][0]["translatedText"])