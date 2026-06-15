# -*- coding: utf-8 -*-
"""
測試 Ollama 圖片輸入
"""

import requests
import base64
import json
import sys

# 強制 UTF-8 編碼
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer)
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer)

# 圖片路徑
IMAGE_PATH = r"C:\Users\danny\.openclaw\workspace\data_files\螢幕擷取畫面 2026-05-10 100924.png"
MODEL = "gemma4:e4b-it-q4_K_M"

# 讀取圖片並轉 base64
with open(IMAGE_PATH, 'rb') as f:
    image_data = base64.b64encode(f.read()).decode('utf-8')

# 構建請求
url = "http://localhost:11434/api/generate"
payload = {
    "model": MODEL,
    "prompt": "請描述這張圖片的內容，包括所有可見的文字和介面元素。",
    "images": [image_data],
    "stream": False
}

print(f"發送請求到 {url}...")
print(f"模型: {MODEL}")
print(f"圖片大小: {len(image_data)} bytes (base64)")
print("-" * 50)

# 發送請求
response = requests.post(url, json=payload)
result = response.json()

print("回應:")
print(json.dumps(result, indent=2, ensure_ascii=False))