# -*- coding: utf-8 -*-
"""
測試 Ollama CLI 圖片輸入 - 修復版
使用 stderr=DEVNULL 避免阻塞
"""

import subprocess
import sys
import time
import re

# 強制 UTF-8 編碼
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer)
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer)

IMAGE_PATH = r"C:\Users\danny\.openclaw\workspace\data_files\螢幕擷取畫面 2026-05-10 100924.png"
MODEL = "gemma4:e4b-it-q4_K_M"
PROMPT = "請描述這張圖片的內容"

print("=" * 60)
print("測試 Ollama CLI 圖片輸入 - stderr=DEVNULL")
print("=" * 60)
print(f"圖片: {IMAGE_PATH}")
print(f"提示: {PROMPT}")
print("-" * 60)

start_time = time.time()

# 關鍵修改：使用 stderr=DEVNULL
process = subprocess.Popen(
    ["ollama", "run", MODEL],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.DEVNULL  # 忽略 stderr
)

# 發送命令
commands = f".image {IMAGE_PATH}\n{PROMPT}\n"
process.stdin.write(commands.encode('utf-8'))
process.stdin.flush()
process.stdin.close()

stdout_buffer = b""
last_update = time.time()
timeout = 120

print("\n[開始讀取輸出...]\n")

while True:
    elapsed = time.time() - start_time
    if elapsed > timeout:
        print(f"\n[超時 {timeout}秒]")
        break
    
    # 只讀取 stdout
    try:
        chunk = process.stdout.read(256)
        if chunk:
            stdout_buffer += chunk
            last_update = time.time()
            
            # 處理行
            while b'\n' in stdout_buffer:
                line_bytes, stdout_buffer = stdout_buffer.split(b'\n', 1)
                line = line_bytes.decode('utf-8', errors='replace')
                
                # 移除 ANSI
                line = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', line)
                line = line.strip()
                
                if line:
                    print(f"[{elapsed:.1f}s] {line[:150]}")
    except Exception as e:
        print(f"[讀取錯誤] {e}")
        break
    
    # 檢查進程結束
    if process.poll() is not None:
        # 處理剩餘
        if stdout_buffer:
            remaining = stdout_buffer.decode('utf-8', errors='replace')
            remaining = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', remaining)
            if remaining.strip():
                print(f"[END] {remaining.strip()[:150]}")
        break
    
    # 每 10 秒顯示進度
    if int(elapsed) % 10 == 0 and int(elapsed) > 0 and elapsed - int(elapsed) < 0.5:
        print(f"[進度] {elapsed:.1f}秒, buffer: {len(stdout_buffer)} bytes")
    
    time.sleep(0.05)

process.wait()

end_time = time.time()
print(f"\n{'=' * 60}")
print(f"測試完成")
print(f"耗時: {end_time - start_time:.2f} 秒")
print(f"總輸出: {len(stdout_buffer)} bytes")
print(f"=" * 60)