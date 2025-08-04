import requests
import warnings
from typing import Callable
import urllib.parse
import json 
import fetch_paper
import time
from dataclasses import dataclass
from typing import List, Dict, Union
import xml.etree.ElementTree as ET
from urllib.parse import unquote
ACCESS_TOKEN="sk-VN48920329mF334e414B"

PROMPT="你是一名研究人员，请你根据当前给出的论文摘要，给出一份500字的论文小结，。"

@dataclass
class MessageContent:
    """思考过程的内容结构"""
    status: str
    content: str
    time: str

@dataclass
class Message:
    """消息对象"""
    type: str
    id: str
    content: Union[str, MessageContent]  # 可以是字符串或MessageContent对象
    
    def __post_init__(self):
        # 如果content是字典，自动转换为MessageContent对象
        if isinstance(self.content, dict):
            self.content = MessageContent(
                status=self.content.get("status", ""),
                content=self.content.get("content", ""),
                time=self.content.get("time", "")
            )

@dataclass
class ParsedData:
    """解析后的完整数据结构"""
    plugin_code: str
    session_id: str
    question_id: str
    answer_id: str
    messages: List[Message]
    isend: bool
    
    @classmethod
    def from_raw_data(cls, raw_data: str):
        """从原始数据创建解析对象"""
        # 清理数据（去除外层引号和转义符）
        cleaned = raw_data.strip('"')
        
        # 解析 XML
        root = ET.fromstring(f"<root>{cleaned}</root>")
        
        # 提取基础信息
        plugin_code = root.find("pluginCode").text
        session_id = root.find("sessionId").text
        question_id = root.find("questionId").text
        answer_id = root.find("answerId").text
        isend = True if root.find("end") else False
        
        # 处理 markdown 内容
        markdown_data = unquote(root.find("markdown").text)
        messages_json = json.loads(markdown_data)
        
        # 创建Message对象列表
        messages = [
            Message(type=msg["type"], id=msg["id"], content=msg["content"])
            for msg in messages_json
        ]
        
        return cls(
            plugin_code=plugin_code,
            session_id=session_id,
            question_id=question_id,
            answer_id=answer_id,
            messages=messages,
            isend=isend
        )
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

def demo_callback(content: str):
        """简单的控制台打印回调"""
        if content.startswith('[ERROR]'):
            print(f"\033[31m{content}\033[0m")
        else:
            # if has end res= response 
            print(f"{content}",end='')

 
def handle_text_stream(url: str,
                       access_token: str,
                       payload: dict,
                       callback: Callable[[str], None]=demo_callback,
                       chunk_size: int = 1024,
                       delimiter: str = '\n\n') -> str:
    """
    Core method for handling plain text SSE streaming responses

    Parameters:
    url: Streaming API endpoint
    access_token: Authentication token
    payload: Request payload dictionary
    callback: Callback function triggered when receiving complete events
    chunk_size: Network read chunk size (bytes)
    delimiter: Event delimiter (default SSE standard double newline)
    """
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'text/event-stream',
        'Content-Type': 'application/json'
    }
    
    past_token=''
    past_id=0
    past_len=0
    buffer = ''  # Cross-chunk buffer

    try:
        with requests.post(url,
                           headers=headers,
                           json=payload,
                           stream=True,
                           timeout=(3.05, 30)) as resp:

            resp.raise_for_status()
            print(f'{resp=}')
            for byte_chunk in resp.iter_content(chunk_size=chunk_size):
                if not byte_chunk:
                    continue
                # Decode and handle encoding issues
                try:
                    text_chunk = byte_chunk.decode('utf-8')
                except UnicodeDecodeError:
                    text_chunk = byte_chunk.decode('utf-8', errors='replace')
                    warnings.warn("Detected non-UTF-8 characters, replaced malformed bytes")
                buffer += text_chunk
                # Split complete events
                while delimiter in buffer:
                    event_raw, buffer = buffer.split(delimiter, 1)
                    res=process_sse_event(event_raw.strip(),callback=None)
                    if not  res:
                        continue
                    
                    decode_msg=ParsedData.from_raw_data(res)
                    markdown_contents=decode_msg.messages
                    cur_message= markdown_contents[-1]
                    time.sleep(0)
                    cur_id=int(cur_message.id)

                    if cur_message.type == 'Thinking':
                        cur_token=fully_url_decode(cur_message.content.content)
                    elif cur_message.type == 'MarkDown':
                        cur_token=fully_url_decode(cur_message.content)
                    else:
                        cur_token=''
                        print(f"输出的contents type 未处理")
                        print(f"{cur_message=}")
                    cur_len=len(cur_token)
                    if cur_id== past_id:
                        assert cur_len>=past_len
                        if  past_len>0 and cur_len==past_len:
                            # if decode_msg.isend !=True:
                                continue
                        new_token=cur_token[-(cur_len-past_len):]
                        past_token=cur_token
                        past_len=cur_len
                        callback(new_token)
                    else:
                        past_id=cur_id
                        past_token=''
                        past_len=0
                        print(f"\n ***$$$ 开启新type {cur_message.type} 1111 \n")
            return cur_token
    except requests.exceptions.RequestException as e:
        error_msg = f"Streaming connection error: {str(e)}"
        if buffer:
            error_msg += f"\nUnprocessed buffer: {buffer[:200]}{'...' if len(buffer) > 200 else ''}"
        callback(f"[ERROR] {error_msg}")


def process_sse_event(raw_event: str, callback: Callable[[str], None]) -> str:
    """
    Parse SSE event format and extract plain text content

    SSE event example:
    data: First line content
    data: Second line content
    """
    event_lines = [line.strip() for line in raw_event.split('\n') if line.strip()]
    content_lines = []

    for line in event_lines:
        if line.startswith('data:'):
            # Extract data field content (allowing leading spaces)
            content = line.lstrip()
            content_lines.append(content)
        elif line.startswith(':'):
            # Ignore comment lines
            continue

    # Merge multi-line data content
    full_content = '\n'.join(content_lines)
    return full_content
    if full_content:
       
        return callback(full_content)


def get_summary(text,prompt=PROMPT,chunk_size=1024,delimiter: str = '\n\n'):
    if text is None:
        return ""
    text=prompt+ text
    # get session id
    try:
        sessionid_result = make_authenticated_request(
            url="https://geogpt.zero2x.org.cn/be-api/service/api/geoChat/generate",
            access_token=ACCESS_TOKEN
        )
        res_data=sessionid_result.get('data')
        session_id = res_data.get('data')

    except requests.exceptions.RequestException as e:
        print(f"请求发生错误: {e}")


    if session_id :
        
        try:
            result=handle_text_stream(
                url="https://geogpt.zero2x.org.cn/be-api/service/api/geoChat/sendMsg",
                access_token=ACCESS_TOKEN,
                payload={
                    "text": text,
                    "sessionId": session_id,
                    "module": "GeoGPT-R1-Preview" #[ Qwen2.5-72B-GeoGPT , GeoGPT-R1-Preview , DeepSeekR1-GeoGPT ]
                },
                #  call_back ,
                chunk_size=chunk_size,
                delimiter=delimiter
            )
  
            return result
        except KeyboardInterrupt:
            print("\n用户主动终止连接")
    
# 使用示例
# 发送消息 开始对话
if __name__ == "__main__":
    papers = fetch_paper.load_paper_list()
    papers=fetch_paper.fetch_paper(papers)
    text=' '.join([paper.get('abstract')  for paper in papers if  paper.get('abstract')  is not None])
    # text='你好,输出5个字'
    # get session id

    res=get_summary(text,prompt="")
    print(f"{res=}")
    # try:
    #     result = make_authenticated_request(
    #         url="https://geogpt.zero2x.org.cn/be-api/service/api/geoChat/generate",
    #         access_token=ACCESS_TOKEN
    #     )
    #     #  result 数据结构
    #     #         {
    #     #     "code": "00000",
    #     #     "msg": null,
    #     #     "data": "11535115-9f0c-4c07-9da8-71db5648625b",
    #     #     "traceId": "39960dcff0df420c9e309b695c103914"
    #     # }
    #     print(f"响应状态码: {result['status_code']}")
    #     # print(f"响应数据: {result['data']}")
    #     res_data=result.get('data')
    #     session_id = res_data.get('data')

    #     print(f'{session_id=}')
    # except requests.exceptions.RequestException as e:
    #     print(f"请求发生错误: {e}")
    
    # def demo_callback(content: str):
    #     """简单的控制台打印回调"""
    #     if content.startswith('[ERROR]'):
    #         print(f"\033[31m{content}\033[0m")
    #     else:
    #         print(f"收到内容: {content}")

    # if session_id :
            
    #     try:
    #         res=handle_text_with_result(
    #             url="https://geogpt.zero2x.org.cn/be-api/service/api/geoChat/sendMsg",
    #             access_token=ACCESS_TOKEN,
    #             payload={
    #                 "text": text,
    #                 "sessionId": session_id,
    #                 "module": "GeoGPT-R1-Preview" #[ Qwen2.5-72B-GeoGPT , GeoGPT-R1-Preview , DeepSeekR1-GeoGPT ]
    #             },
    #             callback=demo_callback
    #         )
    #         print(res)
    #     except KeyboardInterrupt:
    #         print("\n用户主动终止连接")

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


