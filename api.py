import requests
import requests
import warnings
from typing import Callable
import urllib.parse
import json

ACCESS_TOKEN="sk-VN48920329mF334e414B"

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

def handle_text_stream(url: str,
                       access_token: str,
                       payload: dict,
                       callback: Callable[[str], None],
                       chunk_size: int = 1024,
                       delimiter: str = '\n\n') -> None:
    """
    处理纯文本SSE流式响应的核心方法

    参数说明：
    url: 流式接口端点
    access_token: 认证令牌
    payload: 请求负载字典
    callback: 每收到一个完整事件时触发的回调函数
    chunk_size: 网络读取块大小（字节）
    delimiter: 事件分隔符（默认SSE标准的双换行）
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'text/event-stream',
        'Content-Type': 'application/json'
    }

    buffer = ''  # 跨数据块的缓冲区
    try:
        with requests.post(url,
                           headers=headers,
                           json=payload,
                           stream=True,
                           timeout=(3.05, 30)) as resp:

            resp.raise_for_status()

            for byte_chunk in resp.iter_content(chunk_size=chunk_size):
                if not byte_chunk:
                    continue

                # 解码并处理编码问题
                try:
                    text_chunk = byte_chunk.decode('utf-8')
                    # text_chunk = fully_url_decode(byte_chunk)
                    # print("收到 chunk text 进行decode 处理")
                except UnicodeDecodeError:
                    text_chunk = byte_chunk.decode('utf-8', errors='replace')
                    warnings.warn("检测到非UTF-8编码字符，已替换异常编码点")



                buffer += text_chunk

                # 分割完整事件
                while delimiter in buffer:
                    event_raw, buffer = buffer.split(delimiter, 1)
                    process_sse_event(event_raw.strip(), callback)

    except requests.exceptions.RequestException as e:
        error_msg = f"流式连接异常: {str(e)}"
        if buffer:
            error_msg += f"\n未处理缓冲数据: {buffer[:200]}{'...' if len(buffer) > 200 else ''}"
        callback(f"[ERROR] {error_msg}")


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


# 使用示例
# 发送消息 开始对话
if __name__ == "__main__":
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
                    "text": "你好呀",
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