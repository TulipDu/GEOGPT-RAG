import streamlit as st
import requests
import api
import fetch_paper
import pandas as pd

# 1. 输入 API Key 和指令
api_key = st.sidebar.text_input("GeoGPT API Key", type="password")
prompt = st.text_area("请输入您的问题")
data = fetch_paper.load_paper_list()
# st.write(data)


# 2. 触发请求
if st.button("List"):
    titles = [paper["title"] for paper in data]
    citationCount = [paper["citationCount"] for paper in data]
    
    st.subheader("📚 论文列表", divider="rainbow")
    
    # 创建可交互的Dataframe
    df = pd.DataFrame({
        "ID": range(1, len(titles)+1),
        "Title": titles,
        "CitationCount": citationCount
    })
    
    st.dataframe(
        df,
        column_config={
            "ID": st.column_config.NumberColumn(width="small"),
            "Title": st.column_config.TextColumn(width="large"),
            "CitationCount": st.column_config.TextColumn(width="small")
        },
        hide_index=True,
        use_container_width=True
    )

if st.button("Find related papers"):
    list = fetch_paper.fetch_paper(data)

    titles = [paper["title"] for paper in list]
    citationCount = [paper["citationCount"] for paper in list]
    summary = [api.get_summary(paper['abstract']) for paper in list]
    
    st.subheader("📚 论文列表", divider="rainbow")

    # for paper in list:
    #     st.write(f"**{paper['title']}**")
    #     st.write(f"引用次数: {paper['citationCount']}")
    #     st.button(f"**{paper['title']}**", on_click=lambda x : print("Hello World!"))
    #     # st.write(f"Fetching details for {paper['title']}...")
    
    # # 创建可交互的Dataframe
    df = pd.DataFrame({
        "ID": range(1, len(titles)+1),
        "Title": titles,
        "CitationCount": citationCount,
        "Summary": summary
    })
    
    st.dataframe(
        df,
        column_config={
            "ID": st.column_config.NumberColumn(width="small"),
            "Title": st.column_config.TextColumn(width="large"),
            "CitationCount": st.column_config.TextColumn(width="small"),
            "Summary": st.column_config.TextColumn(width="small")
        },
        hide_index=True,
        use_container_width=True
    )


    

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

