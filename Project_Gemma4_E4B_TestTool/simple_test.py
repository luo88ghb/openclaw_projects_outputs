# -*- coding: utf-8 -*-
"""
Gemma 4 E4B 簡易測試腳本
===========================
最簡化版本：只測試一次推論流程

流程：
1. 檢查模型狀態
2. 載入模型
3. 發送 500 字推論任務
4. 接收輸出
5. 記錄時間、狀態、格式
6. 卸載模型

作者：Zeni (傑尼)
更新：2026-05-11
"""

import subprocess
import time
import json
import re
import sys
from datetime import datetime

# 強制 UTF-8 編碼
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer)
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer)

# ========== 設定 ==========
MODEL_NAME = "gemma4:e4b-it-q4_K_M"
TEST_PROMPT = """請用繁體中文回答以下問題，字數約 500 字：

什麼是人工智慧？請從定義、發展歷史、應用領域三個方面進行說明。"""

def log(msg):
    """輸出日誌"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def check_model_status():
    """檢查模型狀態"""
    log("檢查模型狀態...")
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            timeout=10
        )
        if MODEL_NAME in result.stdout.decode('utf-8', errors='replace'):
            log(f"✅ 模型已存在: {MODEL_NAME}")
            return True
        log(f"❌ 模型不存在: {MODEL_NAME}")
        return False
    except Exception as e:
        log(f"❌ 檢查失敗: {e}")
        return False

def check_vram_usage():
    """檢查 VRAM 使用狀態"""
    log("檢查 VRAM 狀態...")
    try:
        result = subprocess.run(
            ["ollama", "ps"],
            capture_output=True,
            timeout=10
        )
        output = result.stdout.decode('utf-8', errors='replace')
        if MODEL_NAME in output:
            # 解析狀態
            lines = output.strip().split('\n')
            if len(lines) > 1:
                parts = lines[1].split()
                if len(parts) >= 3:
                    log(f"📊 模型狀態: {parts[0]} | 大小: {parts[2]} | 狀態: {parts[-1] if len(parts) > 5 else 'running'}")
            return True
        log("📋 模型未載入 VRAM")
        return False
    except Exception as e:
        log(f"❌ VRAM 檢查失敗: {e}")
        return False

def run_simple_test():
    """執行簡易測試"""
    log("=" * 60)
    log("開始簡易推論測試")
    log("=" * 60)
    
    # 步驟 1: 檢查模型
    if not check_model_status():
        return {"success": False, "error": "模型不存在"}
    
    # 步驟 2: 檢查 VRAM
    check_vram_usage()
    
    # 步驟 3: 執行推論
    log("發送推論任務...")
    start_time = time.time()
    output_chunks = []
    total_chars = 0
    
    try:
        # 使用 binary 模式，避免編碼問題
        process = subprocess.Popen(
            ["ollama", "run", MODEL_NAME],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL  # 忽略 stderr 避免 cp950 問題
        )
        
        # 發送 prompt (UTF-8 編碼)
        process.stdin.write(TEST_PROMPT.encode('utf-8'))
        process.stdin.write(b"\n")
        process.stdin.flush()
        process.stdin.close()
        
        # 讀取輸出 (binary 模式)
        buffer = b""
        last_update = time.time()
        timeout = 120  # 2 分鐘超時
        
        while True:
            elapsed = time.time() - start_time
            if elapsed > timeout:
                log(f"⏱️ 超時 ({timeout}秒)，停止讀取")
                process.terminate()
                break
            
            # 讀取資料 (binary)
            try:
                chunk = process.stdout.read(128)
                if not chunk:
                    # 檢查是否結束
                    if process.poll() is not None:
                        # 處理剩餘 buffer
                        if buffer:
                            try:
                                remaining = buffer.decode('utf-8', errors='replace')
                                # 移除 ANSI 轉義序列
                                remaining = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', remaining)
                                output_chunks.append(remaining)
                                total_chars += len(remaining)
                            except:
                                pass
                        break
                    time.sleep(0.05)
                    continue
                
                buffer += chunk
                last_update = time.time()
                
                # 處理完整行
                while b'\n' in buffer:
                    line_bytes, buffer = buffer.split(b'\n', 1)
                    try:
                        line = line_bytes.decode('utf-8', errors='replace')
                    except:
                        line = line_bytes.decode('utf-8', errors='replace')
                    
                    # 移除 ANSI 轉義序列
                    line = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', line)
                    line = line.strip()
                    
                    if line and not line.startswith('['):
                        output_chunks.append(line)
                        total_chars += len(line)
                        
                        # 每 10 秒顯示進度
                        if int(elapsed) % 10 == 0 and int(elapsed) > 0:
                            log(f"📝 已接收 {total_chars} 字元 ({elapsed:.1f}秒)")
            
            except Exception as e:
                log(f"❌ 讀取錯誤: {e}")
                break
        
        # 等待進程結束
        process.wait()
        
    except Exception as e:
        log(f"❌ 執行錯誤: {e}")
        return {"success": False, "error": str(e)}
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    # 步驟 4: 處理結果
    full_output = "".join(output_chunks)
    
    # 移除多餘空白
    full_output = re.sub(r'\s+', ' ', full_output).strip()
    
    log("=" * 60)
    log("測試完成")
    log("=" * 60)
    
    # 步驟 5: 分析結果
    result = {
        "success": True,
        "elapsed_seconds": round(elapsed, 2),
        "total_chars": len(full_output),
        "chars_per_second": round(len(full_output) / elapsed, 2) if elapsed > 0 else 0,
        "output_preview": full_output[:500] + "..." if len(full_output) > 500 else full_output,
        "output_full": full_output,
        "timestamp": datetime.now().isoformat()
    }
    
    # 輸出結果
    log(f"⏱️ 耗時: {result['elapsed_seconds']} 秒")
    log(f"📝 總字數: {result['total_chars']} 字")
    log(f"📊 速度: {result['chars_per_second']} 字/秒")
    log(f"📋 預覽: {result['output_preview'][:200]}...")
    
    return result

def unload_model():
    """卸載模型"""
    log("卸載模型...")
    try:
        # 發送卸載指令
        subprocess.Popen(
            ["ollama", "stop", MODEL_NAME],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        log(f"📤 已發送卸載指令: ollama stop {MODEL_NAME}")
        
        # 等待卸載完成
        time.sleep(5)
        
        # 檢查是否卸載成功
        for i in range(10):
            result = subprocess.run(
                ["ollama", "ps"],
                capture_output=True,
                timeout=10
            )
            if MODEL_NAME not in result.stdout.decode('utf-8', errors='replace'):
                log(f"✅ 模型已卸載 (等待 {i+1} 秒)")
                return True
            time.sleep(1)
        
        log("⚠️ 模型可能仍在卸載中，請手動確認")
        return False
        
    except Exception as e:
        log(f"❌ 卸載錯誤: {e}")
        return False

def main():
    """主程序"""
    log("=" * 60)
    log("Gemma 4 E4B 簡易測試")
    log(f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 60)
    
    # 執行測試
    result = run_simple_test()
    
    # 卸載模型
    unload_model()
    
    # 儲存結果
    filename = f"simple_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        log(f"📁 結果已儲存: {filename}")
    except Exception as e:
        log(f"❌ 儲存失敗: {e}")
    
    log("=" * 60)
    log("測試結束")
    log("=" * 60)
    
    return result

if __name__ == "__main__":
    main()