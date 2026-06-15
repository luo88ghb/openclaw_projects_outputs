import json
import requests # 使用 requests 會比 urllib 方便處理

def send_to_comfy(main_img, pose_img):
    url = "http://127.0.0.1:8188/prompt"
    workflow_path = r"C:\Users\danny\Downloads\Qwen-Image-Edit2511+AnyPose免骨架姿态迁移lora，4+步高效出图.json"
    
    with open(workflow_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 修改圖片節點
    for node in data["nodes"]:
        if node["id"] == 146: # 主體圖
            node["widgets_values"][0] = main_img
        if node["id"] == 143: # 姿態圖
            node["widgets_values"][0] = pose_img
            
    # 對於介面格式的 JSON，某些 ComfyUI 版本支援直接 POST 整個 JSON
    # 但標準 API 需要的是 prompt 字典。
    # 這裡我們嘗試發送這份修改後的數據
    
    payload = {
        "client_id": "zeni_assistant",
        "prompt": data # 某些插件支援解析這種格式
    }
    
    try:
        # 如果直接發送失敗，我們改用 websocket 模擬或是提示羅哥
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        return str(e)

if __name__ == "__main__":
    # 這是最後一次嘗試 API 方式，如果不行，傑尼會建議羅哥手動匯出 API JSON
    res = send_to_comfy("01_qwenedit_00033_.png", "@cutiejp☁️.jpeg")
    print(res)
