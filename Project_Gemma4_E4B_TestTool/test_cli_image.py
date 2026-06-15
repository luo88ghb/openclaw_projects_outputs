# -*- coding: utf-8 -*-
"""
測試 Ollama CLI 圖片輸入
"""

import subprocess
import sys
import time

# 強制 UTF-8 編碼
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer)
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer)

IMAGE_PATH = r"C:\Users\danny\.openclaw\workspace\data_files\螢幕擷取畫面 2026-05-10 100924.png"
MODEL = "gemma4:e4b-it-q4_K_M"
PROMPT = "請描述這張圖片的內容"

print("=" * 60)
print("測試 Ollama CLI 圖片輸入")
print("=" * 60)

# 方法 1: 使用 .image 命令
print("\n[方法 1] 使用 .image 命令")
print("-" * 40)

process = subprocess.Popen(
    ["ollama", "run", MODEL],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE
)

# 嘗試發送 .image 命令
commands = f".image {IMAGE_PATH}\n{PROMPT}\n"
process.stdin.write(commands.encode('utf-8'))
process.stdin.flush()
process.stdin.close()

stdout, stderr = process.communicate(timeout=60)
print(f"stdout: {stdout.decode('utf-8', errors='replace')[:500]}")
print(f"stderr: {stderr.decode('utf-8', errors='replace')[:500]}")

print("\n" + "=" * 60)
print("測試完成")