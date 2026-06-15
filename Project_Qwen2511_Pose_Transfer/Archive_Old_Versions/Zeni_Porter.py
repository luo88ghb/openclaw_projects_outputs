import os
# 強制開啟高速下載模式
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"

from huggingface_hub import snapshot_download

model_id = "Qwen/Qwen-Image-Edit-2511"
print(f"🐢 傑尼正在幫你加速搬運模型：{model_id}")
print("這會使用 Rust 編寫的核心進行多執行緒下載，通常比瀏覽器快很多！")

try:
    path = snapshot_download(
        repo_id=model_id,
        repo_type="model",
        resume_download=True,
        max_workers=8
    )
    print(f"\n✅ 搬運完成！模型已存放在：{path}")
except Exception as e:
    print(f"\n❌ 搬運失敗：{e}")
    print("羅哥，如果看到連線超時，請檢查網路，或者試試看開啟 VPN (如果有的話)。")
