import streamlit as st
import requests
import api
import fetch_paper
import pandas as pd

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
data = fetch_paper.load_paper_list()
# st.write(data)


# 2. 触发请求
if st.button(
    "📋 List Papers", 
    help="点击显示今日精选论文列表，包含标题和引用次数信息"
):
    titles = [paper["title"] for paper in data]
    citationCount = [paper["citationCount"] for paper in data]
    
    st.subheader("📚 今日精选论文", divider="rainbow")
    
    # 创建可交互的Dataframe
    df = pd.DataFrame({
        "序号": range(1, len(titles)+1),
        "论文标题": titles,
        "引用次数": citationCount
    })
    
    # 添加CSS实现自动换行
    st.markdown("""
    <style>
        /* 表格自动换行 */
        div[data-testid="stDataFrame"] div[data-testid="stDataFrameCell"] {
            white-space: normal !important;
            word-break: break-word !important;
        }
        
        /* 增大行高 */
        div[data-testid="stDataFrame"] div[data-testid="stDataFrameRow"] {
            min-height: 60px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.dataframe(
        df,
        column_config={
            "序号": st.column_config.NumberColumn(
                width="small",
                help="论文序号，从1开始"
            ),
            "论文标题": st.column_config.TextColumn(
                width="large",
                help="论文完整标题，点击可排序"
            ),
            "引用次数": st.column_config.NumberColumn(
                help="论文被引用的次数，点击可排序",
                format="%d 次"
            )
        },
        hide_index=True,
        use_container_width=True
    )


if st.button(
        "🔍 Find related papers",
        help="点击查找与今日论文相关的研究，获取更多引用和摘要信息"
    ):
    # 添加加载状态提升用户体验
    with st.spinner('正在查找相关论文...'):
        list = fetch_paper.fetch_paper(data)
        titles = [paper["title"] for paper in list]
        citationCount = [paper["citationCount"] for paper in list]
        summary = [api.get_summary(paper['abstract']) for paper in list]
    
    st.subheader("📚 论文列表", divider="rainbow")
    
    # 创建自适应高度的表格
    df = pd.DataFrame({
        "ID": range(1, len(titles)+1),
        "Title": titles,
        "Citations": citationCount,
        "Summary": summary
    })
    
    # 使用CSS实现自动换行
    st.markdown("""
    <style>
        /* 设置表格自动换行 */
        div[data-testid="stDataFrame"] div[data-testid="stDataFrameCell"] {
            white-space: normal !important;
            word-break: break-word !important;
        }
        
        /* 增大行高 */
        div[data-testid="stDataFrame"] div[data-testid="stDataFrameRow"] {
            min-height: 100px;
        }
        
        /* 标题列加粗 */
        div[data-testid="stDataFrame"] div[data-testid="stDataFrameColumnHeader"] {
            font-weight: bold;
            background-color: #f0f2f6;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # 显示表格
    st.dataframe(
        df,
        column_config={
            "ID": st.column_config.NumberColumn(
                "序号", 
                width="small",
                help="论文序号"
            ),
            "Title": st.column_config.TextColumn(
                "论文标题",
                width="large",
                help="论文完整标题"
            ),
            "Citations": st.column_config.NumberColumn(
                "引用次数",
                help="论文被引用次数",
                format="%d 次"
            ),
            "Summary": st.column_config.TextColumn(
                "摘要",
                width="large",
                help="论文摘要"
            )
        },
        hide_index=True,
        use_container_width=True
    )
    

    

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

