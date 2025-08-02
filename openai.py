from openai import OpenAI

client = OpenAI(
    # This is the default and can be omitted
    api_key="sk-VN48920329mF334e414B",
)

# 导入所需库
# 注意，此处我们假设你已根据上文配置了 OpenAI API Key，如没有将访问失败
completion = client.chat.completions.create(
    # 调用模型：ChatGPT-4o
    model="Qwen2.5",
    # messages 是对话列表
    messages=[
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ]
)
