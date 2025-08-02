import streamlit as st
import requests

# 1. 输入 API Key 和指令
api_key = st.sidebar.text_input("GeoGPT API Key", type="password")
prompt = st.text_area("输入地理任务描述")

# 2. 触发请求
if st.button("执行任务"):
    if not api_key or not prompt:
        st.error("请填写 API Key 和任务描述。")
    else:
        headers = {"Authorization": f"Bearer {api_key}"}
        json_payload = {
            "model": "qwen2.5-geo",  # 或其他 GeoGPT 模型
            "prompt": prompt,
            "tools": ["Buffer", "Intersect", "Map"],  # 根据文档配置
        }
        resp = requests.post("https://geogpt.zero2x.org.cn/be-api/service/api/geoChat/sendMsg",
                             headers=headers, json=json_payload)
        try:
            data = resp.json()
        except Exception as e:
            print("解析 JSON 失败，原因：", e)
        
        # 3. 展示结果示例
        st.write("**推理结果：**", data.get("response_text"))
        if "geojson" in data:
            st.map(data["geojson"])

# 4. 性能优化建议
# @st.cache_data 用于缓存重复请求
# 启用 `streamlit run your_app.py --server.maxMessageSize 200` 如需处理大型 GeoJSON
