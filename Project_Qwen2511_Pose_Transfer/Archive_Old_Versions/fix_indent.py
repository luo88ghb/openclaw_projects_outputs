import sys, os

file_path = r'C:\Users\danny\.openclaw\workspace\Zeni_Engine_v9_Pro.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

part3_old = '''if st.session_state.get('start_actual_run', False):
    st.session_state.start_actual_run = False
    
    log_placeholder = st.empty()
    status_box = st.status("🚀 正在執行 Jojo 實戰任務...", expanded=True)
    
    try:'''

part3_new = '''if st.session_state.get('start_actual_run', False):
    st.session_state.start_actual_run = False
    
    if True:
        log_placeholder = st.empty()
        status_box = st.status("🚀 正在執行 Jojo 實戰任務...", expanded=True)
        
        try:'''

content = content.replace(part3_old, part3_new)

# Update the API key line as well to hardcode the new key
api_key_old = '''    api_key = os.getenv("GEMINI_API_KEY")'''
api_key_new = '''    api_key = os.getenv("GEMINI_API_KEY", "AIzaSyA_vh_HcPd0xE8KfatK9-RcJEf89RZ2K-k")'''
content = content.replace(api_key_old, api_key_new)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print('Success')