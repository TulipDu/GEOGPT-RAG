import streamlit as st
import api
import fetch_paper

st.set_page_config(layout="wide")  # 使用宽屏布局获得更好的表格显示
st.header("📚 每日论文速递", divider="rainbow")

# 添加页面说明
with st.expander("ℹ️ 使用说明", expanded=True):
    st.markdown("""
    **欢迎使用每日论文速递系统！**
    - 点击 **List Papers** 按钮显示今日精选论文
    - 点击 **Find related papers** 按钮获取更多相关研究
    - 将鼠标悬停在按钮或表格标题上可查看详细说明
    """)
# 1. 输入 API Key 和指令
# api_key = st.sidebar.text_input("GeoGPT API Key", type="password")
# prompt = st.text_area("请输入您的问题")
st.session_state.data = fetch_paper.load_paper_list()
# st.write(data)


# 2. 触发请求

for paper in st.session_state.data:
    col1, col2 = st.columns([4, 1])
    with col1:
        st.subheader(paper['title'])
    with col2:
        st.metric("citationCount", paper['citationCount'])
    st.divider()

if st.button(
        "🔍 Find related papers",
        help="点击查找与今日论文相关的研究，获取更多引用和摘要信息"
    ):
    # 添加加载状态提升用户体验
    with st.spinner('正在查找相关论文...'):
        st.session_state["fetched"] = fetch_paper.fetch_paper(st.session_state.data)
        if "summary" in st.session_state:
            del st.session_state.summary


if "fetched" in st.session_state:
    if "fetched_remove_index" in st.session_state:
        del st.session_state.fetched[st.session_state.fetched_remove_index]
        del st.session_state.fetched_remove_index
    titles = [paper["title"] for paper in st.session_state.fetched]
    citationCount = [paper["citationCount"] for paper in st.session_state.fetched]
    abstracts = "\n\n".join([paper["abstract"] for paper in st.session_state.fetched if paper["abstract"]])
    
    st.subheader("📚 论文列表", divider="rainbow")
    for i, paper in enumerate(st.session_state.fetched):
        col1, col2, col3 = st.columns([4, 1, 1])
        with col1:
            st.subheader(paper['title'])
        with col2:
            st.metric("citationCount", paper['citationCount'])
        with col3:
            if st.button("Add", key=f"btn_{i}"):
                # st.session_state["added_paper"] = paper
                st.session_state.data.append(paper)
                fetch_paper.save_paper_list(st.session_state.data)
                st.session_state.fetched_remove_index = i
                st.rerun()
        st.divider()
    if "summary" not in st.session_state: 
        with st.spinner("Summarizing..."):
            st.session_state.summary = api.get_summary(abstracts)
            st.session_state.summary = st.session_state.summary.replace("\\n", "\n")  # 替换换行符为 Markdown 换行
    st.markdown(st.session_state.summary)
    
# if st.button("执行任务"):
#     if not api_key or not prompt:
#         st.error("请填写 API Key 和任务描述。")
#     else:
        

#         headers = {"Authorization": f"Bearer {api_key}"}
#         json_payload = {
#             "model": "qwen2.5-geo",  # 或其他 GeoGPT 模型
#             "prompt": prompt,
#             "tools": ["Buffer", "Intersect", "Map"],  # 根据文档配置
#         }
#         resp = requests.post("https://geogpt.zero2x.org.cn/be-api/service/api/geoChat/sendMsg",
#                              headers=headers, json=json_payload)
#         try:
#             data = resp.json()
#         except Exception as e:
#             print("解析 JSON 失败，原因：", e)
        
#         # 3. 展示结果示例
#         st.write("**推理结果：**", data.get("response_text"))
#         if "geojson" in data:
#             st.map(data["geojson"])

