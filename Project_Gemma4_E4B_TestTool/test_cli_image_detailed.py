# -*- coding: utf-8 -*-
"""
測試 Ollama CLI 圖片輸入 - 詳細版
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
print("測試 Ollama CLI 圖片輸入 - 詳細版")
print("=" * 60)
print(f"圖片: {IMAGE_PATH}")
print(f"提示: {PROMPT}")
print("-" * 60)

start_time = time.time()

process = subprocess.Popen(
    ["ollama", "run", MODEL],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE  # 分開 stderr
)

# 發送命令
commands = f".image {IMAGE_PATH}\n{PROMPT}\n"
process.stdin.write(commands.encode('utf-8'))
process.stdin.flush()
process.stdin.close()

# 分別讀取 stdout 和 stderr
stdout_buffer = b""
stderr_buffer = b""

last_update = time.time()
timeout = 120

print("\n[開始讀取輸出...]\n")

while True:
    elapsed = time.time() - start_time
    if elapsed > timeout:
        print(f"\n[超時 {timeout}秒]")
        break
    
    # 讀取 stdout
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
                    print(f"[OUT] {line[:100]}")
    except Exception as e:
        print(f"[讀取錯誤] {e}")
        break
    
    # 讀取 stderr (非阻塞)
    try:
        # 嘗試讀取 stderr
        import select
        if sys.platform != 'win32':
            readable, _, _ = select.select([process.stderr], [], [], 0.01)
            if readable:
                err_chunk = process.stderr.read(256)
                if err_chunk:
                    stderr_buffer += err_chunk
        else:
            # Windows 不支援 select，直接跳過
            pass
    except:
        pass
    
    # 檢查進程結束
    if process.poll() is not None:
        # 處理剩餘
        if stdout_buffer:
            remaining = stdout_buffer.decode('utf-8', errors='replace')
            remaining = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', remaining)
            if remaining.strip():
                print(f"[OUT-REM] {remaining.strip()[:100]}")
        break
    
    # 每 10 秒顯示進度
    if int(elapsed) % 10 == 0 and int(elapsed) > 0 and elapsed - int(elapsed) < 0.5:
        print(f"[進度] {elapsed:.1f}秒, buffer大小: {len(stdout_buffer)} bytes")
    
    time.sleep(0.05)

process.wait()

end_time = time.time()
print(f"\n{'=' * 60}")
print(f"測試完成")
print(f"耗時: {end_time - start_time:.2f} 秒")
print(f"總輸出: {len(stdout_buffer)} bytes")
print(f"=" * 60)