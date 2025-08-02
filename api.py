import requests
import requests
import warnings
from typing import Callable
import urllib.parse
import json 
import fetch_paper
import re
ACCESS_TOKEN="sk-VN48920329mF334e414B"

PROMPT="你是一名研究人员，请你根据当前给出的论文摘要，给出一份论文小结，50字以内。"

def fully_url_decode(s: str) -> str:
    """重复 URL 解码，直到没有 %xx 为止"""
    prev = None
    decoded = s
    while prev != decoded:
        prev = decoded
        decoded = urllib.parse.unquote(decoded)
    return decoded

def clean_json_string(raw_str: str):
    # 1. 完全 URL 解码
    decoded = fully_url_decode(raw_str)

    # 2. 去掉多余的转义，比如 \n、\\ 等
    # 先把 JSON 里的 \\n 转成真正的换行
    decoded = decoded.encode('utf-8').decode('unicode_escape')

    # 3. 如果最外层还是 JSON，就再解析一次
    try:
        json_obj = json.loads(decoded)
        return json_obj
    except json.JSONDecodeError:
        # 不是标准 JSON 就直接返回纯文本
        return decoded

def extract_core_content(raw_content: str) -> str:
    """
    从原始响应中提取核心增量文本
    步骤：1. 提取<markdown>标签内的内容 2. 解析JSON 3. 获取content.content字段
    """
    try:
        # 1. 用正则提取<markdown>标签内的内容（处理可能的引号和转义）
        markdown_match = re.search(r'<markdown>(.*?)</markdown>', raw_content, re.DOTALL)
        if not markdown_match:
            return ""
        markdown_str = markdown_match.group(1).strip()
        
        # 2. 去除可能的外层引号（如示例中的\"）
        markdown_str = re.sub(r'^["\']|["\']$', '', markdown_str)
        
        # 3. 解析JSON（处理可能的转义字符）
        markdown_json = json.loads(markdown_str)
        if isinstance(markdown_json, list) and len(markdown_json) > 0:
            # 提取content.content字段
            thinking_content = markdown_json[0].get("content", {}).get("content", "")
            return thinking_content
        return ""
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        # 解析失败时返回原始内容（便于调试）
        warnings.warn(f"解析核心内容失败: {e}，原始内容: {raw_content[:100]}")
        return ""



# 创建会话窗口 返回会话id
def make_authenticated_request(url, access_token):
    """
    执行带Bearer Token认证的HTTP GET请求
    
    参数：
    url (str): 请求的目标URL
    access_token (str): 访问令牌
    
    返回：
    dict: 包含响应状态码、响应头和响应体的字典
    
    异常：
    requests.exceptions.RequestException: 网络请求相关异常
    """
    headers = {
        'Authorization': f'Bearer {access_token}'
    }
    
    try:
        # 自动处理重定向（默认allow_redirects=True）
        response = requests.get(
            url,
            headers=headers,
            timeout=10  # 建议总是设置超时
        )
        
        # 尝试解析JSON响应，失败则返回文本
        try:
            response_data = response.json()
        except ValueError:
            response_data = response.text
            
        return {
            'status_code': response.status_code,
            'headers': dict(response.headers),
            'data': response_data
        }
        
    except requests.exceptions.RequestException as e:
        # 封装异常信息
        error_info = {
            'error_type': type(e).__name__,
            'error_message': str(e)
        }
        if isinstance(e, requests.exceptions.Timeout):
            error_info['timeout'] = 10
        raise requests.exceptions.RequestException(f"请求失败: {error_info}") from e

def process_sse_event(raw_event: str, callback: Callable[[str], None]) -> None:
    """
    解析SSE事件格式并提取纯文本内容

    SSE事件示例：
    data: 第一行内容
    data: 第二行内容
    """
    event_lines = [line.strip() for line in raw_event.split('\n') if line.strip()]
    content_lines = []

    for line in event_lines:
        if line.startswith('data:'):
            # 提取data字段内容（允许前导空格）
            content = line[5:].lstrip()
            content_lines.append(content)
        elif line.startswith(':'):
            # 忽略注释行
            continue

    # 合并多行data内容
    full_content = '\n'.join(content_lines)
    full_content=fully_url_decode(full_content)
    if full_content:
        callback(full_content)

def handle_text_stream(url: str, access_token: str, payload: dict, callback: Callable[[str], None]):
    """处理流式响应，提取核心内容后调用回调"""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'text/event-stream',
        'Content-Type': 'application/json'
    }
    buffer = ''
    try:
        with requests.post(url, headers=headers, json=payload, stream=True, timeout=(3.05, 30)) as resp:
            resp.raise_for_status()
            for byte_chunk in resp.iter_content(chunk_size=1024):
                if not byte_chunk:
                    continue
                try:
                    text_chunk = byte_chunk.decode('utf-8')
                except UnicodeDecodeError:
                    text_chunk = byte_chunk.decode('utf-8', errors='replace')
                
                buffer += text_chunk
                
                # 按SSE分隔符处理完整事件
                while '\n\n' in buffer:
                    event_raw, buffer = buffer.split('\n\n', 1)
                    # 提取data字段内容
                    data_lines = [line[5:].lstrip() for line in event_raw.split('\n') if line.startswith('data:')]
                    full_event = '\n'.join(data_lines)
                    full_event = fully_url_decode(full_event)
                    
                    # 提取核心增量文本
                    core_content = extract_core_content(full_event)
                    if core_content:
                        callback(core_content)
    except requests.exceptions.RequestException as e:
        callback(f"[ERROR] 流式连接异常: {str(e)}")

def get_summary(prompt,text):
    text=prompt+ text
    # get session id
    try:
        result = make_authenticated_request(
            url="https://geogpt.zero2x.org.cn/be-api/service/api/geoChat/generate",
            access_token=ACCESS_TOKEN
        )
        res_data=result.get('data')
        session_id = res_data.get('data')

    except requests.exceptions.RequestException as e:
        print(f"请求发生错误: {e}")

    def demo_callback(content: str):
        """简单的控制台打印回调"""
        if content.startswith('[ERROR]'):
            print(f"\033[31m{content}\033[0m")
        else:
            print(f"收到内容: {content}")

    if session_id :
        
        try:
            handle_text_stream(
                url="https://geogpt.zero2x.org.cn/be-api/service/api/geoChat/sendMsg",
                access_token=ACCESS_TOKEN,
                payload={
                    "text": text,
                    "sessionId": session_id,
                    "module": "GeoGPT-R1-Preview" #[ Qwen2.5-72B-GeoGPT , GeoGPT-R1-Preview , DeepSeekR1-GeoGPT ]
                },
                callback=demo_callback
            )
        except KeyboardInterrupt:
            print("\n用户主动终止连接")

# 使用示例
# 发送消息 开始对话
if __name__ == "__main__":
    papers = fetch_paper.load_paper_list()
    text=fetch_paper.fetch_paper(papers)[0]
    text= PROMPT
    # get session id
    try:
        result = make_authenticated_request(
            url="https://geogpt.zero2x.org.cn/be-api/service/api/geoChat/generate",
            access_token=ACCESS_TOKEN
        )
        #  result 数据结构
        #         {
        #     "code": "00000",
        #     "msg": null,
        #     "data": "11535115-9f0c-4c07-9da8-71db5648625b",
        #     "traceId": "39960dcff0df420c9e309b695c103914"
        # }
        print(f"响应状态码: {result['status_code']}")
        # print(f"响应数据: {result['data']}")
        res_data=result.get('data')
        session_id = res_data.get('data')

        print(f'{session_id=}')
    except requests.exceptions.RequestException as e:
        print(f"请求发生错误: {e}")
    
    def demo_callback(content: str):
        """简单的控制台打印回调"""
        if content.startswith('[ERROR]'):
            print(f"\033[31m{content}\033[0m")
        else:
            print(f"收到内容: {content}")

    if session_id is not None:
            
        try:
            handle_text_stream(
                url="https://geogpt.zero2x.org.cn/be-api/service/api/geoChat/sendMsg",
                access_token=ACCESS_TOKEN,
                payload={
                    "text": text,
                    "sessionId": session_id,
                    "module": "GeoGPT-R1-Preview" #[ Qwen2.5-72B-GeoGPT , GeoGPT-R1-Preview , DeepSeekR1-GeoGPT ]
                },
                callback=demo_callback
            )
        except KeyboardInterrupt:
            print("\n用户主动终止连接")

# # 使用示例
# if __name__ == "__main__":
#     try:
#         result = make_authenticated_request(
#             url="https://geogpt.zero2x.org.cn/be-api/service/api/geoChat/generate",
#             access_token=ACCESS_TOKEN,
#         )
#         #  result 数据结构
#         #         {
#         #     "code": "00000",
#         #     "msg": null,
#         #     "data": "11535115-9f0c-4c07-9da8-71db5648625b",
#         #     "traceId": "39960dcff0df420c9e309b695c103914"
#         # }
#         print(f"响应状态码: {result['status_code']}")
#         print(f"响应数据: {result['data']}")
#     except requests.exceptions.RequestException as e:
#         print(f"请求发生错误: {e}")

    # 响应状态码: 200
    # 响应数据: {
                # 'code': '00000', 'msg': None, 
                # 'data': '89c11ff0-71aa-43ad-a956-a7ed48a3e56d', 
                # 'traceId': '2a6b9d5a71b2168f23f99caaede41ac7'
    #}

# curl --location 'https://geogpt.zero2x.org.cn/be-api/service/api/geoChat/sendMsg' \
# --header 'Authorization: Bearer sk-VN48920329mF334e414B' \
# --header 'Content-Type: application/json' \
# --data '{
#     "text": "who are you",
#     "sessionId": "017f6e88-170c-48e7-b8a1-c88fe2c22a83",
#     "module": "GeoGPT-R1-Preview"
# }'