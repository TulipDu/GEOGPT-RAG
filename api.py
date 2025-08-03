import requests
import warnings
from typing import Callable
import urllib.parse
import json 
import fetch_paper
import re
import time
from typing import Union, Dict, Any
ACCESS_TOKEN="sk-VN48920329mF334e414B"

PROMPT="你是一名研究人员，请你根据当前给出的论文摘要，给出一份500字的论文小结，。"

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

def demo_callback(content: str):
        """简单的控制台打印回调"""
        if content.startswith('[ERROR]'):
            print(f"\033[31m{content}\033[0m")
        else:
            # if has end res= response 
            print(f"{content}",end='')

def stream_callback(content:str):
    decode_mix_content=decode_mixed_content(content)
    status = decode_mix_content['status']
    assert status == "success"
    decode_full_content=decode_mix_content['content']
  
    markdown_contents=decode_full_content['markdown']
    if 'end' in decode_full_content.keys():
        final_result = markdown_contents[-1]['content']
        print(f"\n ******问题处理完成，结果：{final_result} -------")

 
 

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
                    decode_mix_content=decode_mixed_content(res)
                    status = decode_mix_content['status']
                    assert status == "success"
                    decode_full_content=decode_mix_content['content']
                    markdown_contents=decode_full_content['markdown']

                    time.sleep(0)
                    cur_id=int(markdown_contents[-1]['id'])

                    if markdown_contents[-1]['type'] == 'Thinking':
                        cur_token=markdown_contents[-1]['content']['content']
                    elif markdown_contents[-1]['type'] == 'MarkDown':
                        cur_token=markdown_contents[-1]['content']
                    else:
                        cur_token=''
                        print(f"输出的contents type 未处理")
                        print(f"{markdown_contents=}")
                    cur_len=len(cur_token)
                    if cur_id== past_id:
                        assert cur_len>=past_len
                        if  past_len>0 and cur_len==past_len:
                            time.sleep(1)
                            if 'end' in decode_full_content.keys():
                                final_result = markdown_contents[-1]['content']
                             
                                return final_result
                            else:
                                continue
                        new_token=cur_token[-(cur_len-past_len):]
                        past_token=cur_token
                        past_len=cur_len
                        callback(new_token)
                    else:
                        past_id=cur_id
                        past_token=''
                        past_len=0
                    if 'end' in decode_full_content.keys():
                        final_result = markdown_contents[-1]['content']
                        print(f"******问题处理完成，结果：{final_result} -------")
                        return final_result
    except requests.exceptions.RequestException as e:
        error_msg = f"Streaming connection error: {str(e)}"
        if buffer:
            error_msg += f"\nUnprocessed buffer: {buffer[:200]}{'...' if len(buffer) > 200 else ''}"
        callback(f"[ERROR] {error_msg}")
        return " "



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

def decode_mixed_content(encoded_input: Union[bytes, str]) -> Dict[str, Any]:
    """
    解析包含XML标签的混合结构内容，提取并解码其中的JSON部分
    
    参数:
        encoded_input: 包含XML标签的编码字节流或字符串
        
    返回:
        解析后的的内容字典；若失败则返回错误信息
    """
    try:
        # 1. 字节转字符串并处理基础转义
        if isinstance(encoded_input, bytes):
            raw_str = encoded_input.decode('utf-8', errors='replace')
        else:
            raw_str = encoded_input
   
        # 2. 清理外层包裹（SSE前缀、引号等）
        processed_str = raw_str.replace('\\"', '"')  # 处理转义引号
        processed_str = re.sub(r'^data:"|"$', '', processed_str)  # 移除data:前缀和首尾引号
        processed_str = processed_str.strip()
        
        # 3. 提取所有XML标签内容（返回标签-值字典）
        tag_pattern = re.compile(r'<(\w+)>(.*?)</\1>', re.DOTALL)
        tags = {match[0]: match[1] for match in tag_pattern.findall(processed_str)}
        
        # 4. 对每个标签的值进行URL解码
        decoded_tags = {}
        for tag, value in tags.items():
            # 重复URL解码处理嵌套编码
            decoded_value = value
            prev_value = None
            while prev_value != decoded_value:
                prev_value = decoded_value
                decoded_value = urllib.parse.unquote(decoded_value)
            decoded_tags[tag] = decoded_value
        
        # 5. 尝试解析markdown字段为JSON（如果存在）
        if 'markdown' in decoded_tags:
            decoded_tags['markdown'] = json.loads(decoded_tags['markdown'])
     
        return {
            "status": "success",
            "content": decoded_tags
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": "解析失败",
            "details": str(e),
            "raw_input": str(encoded_input)[:200]
        }


def get_summary(text,prompt=PROMPT,chunk_size=1024,delimiter: str = '\n\n'):
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
  
    # get session id

    res=get_summary(text)
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


