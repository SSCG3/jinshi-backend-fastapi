import gradio as gr
import json
import hmac
import hashlib
import base64
import random
import string
import ssl
import websocket
from datetime import datetime
from time import mktime
from wsgiref.handlers import format_date_time
from urllib.parse import urlparse, urlencode
from queue import Queue
from threading import Thread
import os

# 添加CSS样式
css = """
    footer {display: none !important}

    body {
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }

    .gradio-container { 
        min-height: 0px !important;
        width: 60%;
        margin: auto;
        padding: 0 !important;
        height: 100vh !important;
        display: flex !important;
        flex-direction: column !important;
    }

    body div.gradio-container {
        width: 80% !important;
        max-width: 80% !important;
        margin-left: auto !important;
        margin-right: auto !important;
    }

    #component-0 {
        position: relative !important;
        height: 100% !important;
        box-sizing: border-box !important;
        display: flex !important;
        flex-direction: column !important;
        padding: 10px !important;
    }

    .chat-interface {
        height: calc(100vh - 150px) !important;
        display: flex !important;
        flex-direction: column !important;
    }

    .title-container {
        padding: 10px 0 !important;
    }
"""

# 添加favicon的函数
def get_base64_icon(icon_path):
    try:
        BASE_DIR = "/cs-root/projects/jinshi/backend"  # 指定项目的基础目录
        FAVICON_PATH = os.path.join(BASE_DIR, icon_path)
        with open(FAVICON_PATH, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except Exception as e:
        print(f"Error reading favicon: {e}")
        return None


# 自定义head HTML
def get_custom_head():
    try:
        icon_base64 = get_base64_icon("ceshi/favicon.ico")
        return f"""
            <link rel="icon" type="image/x-icon" 
                  href="data:image/x-icon;base64,{icon_base64}">
        """
    except FileNotFoundError:
        return ""  # 如果没有找到favicon.ico文件，返回空字符串


class LLMClient:
    def __init__(self, app_id, secret, base_url, assistant_code):
        self.app_id = app_id
        self.secret = secret
        self.assistant_code = assistant_code
        self.base_url = base_url
        parsed = urlparse(base_url)
        self.host = parsed.hostname
        self.path = parsed.path

    def create_url(self):
        now = datetime.now()
        date = format_date_time(mktime(now.timetuple()))

        signature_origin = f"host: {self.host}\n"
        signature_origin += f"date: {date}\n"
        signature_origin += f"GET {self.path} HTTP/1.1"

        signature_sha = hmac.new(
            self.secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            digestmod=hashlib.sha256,
        ).digest()

        signature_sha_base64 = base64.b64encode(signature_sha).decode("utf-8")

        authorization_origin = (
            f'hmac api_key="{self.app_id}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature_sha_base64}"'
        )

        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")

        v = {
            "authorization": authorization,
            "date": date,
            "host": self.host,
            "assistantCode": self.assistant_code,
        }

        url = self.base_url + "?" + urlencode(v)
        return url

    def chat(self, text, history):
        message_queue = Queue()

        def on_message(ws, message):
            data = json.loads(message)
            code = data["header"]["code"]
            if code != 0:
                print(f"请求错误: {code}, {data}")
                ws.close()
            else:
                choices = data["payload"]["choices"]
                content = choices["text"][0]["content"]
                status = choices["status"]
                message_queue.put((content, status == 2))

        def on_error(ws, error):
            print("### on_error:", error)
            message_queue.put((f"Error: {str(error)}", True))

        def on_close(ws, close_status_code, close_msg):
            print("### on_close ### code:", close_status_code, " msg:", close_msg)

        def on_open(ws):
            print("### on_open ###")
            data = json.dumps(
                gen_params(
                    trace_id=ws.trace_id,
                    app_id=ws.app_id,
                    assistant_code=ws.assistant_code,
                    content=text,
                )
            )
            ws.send(data)

        def websocket_thread():
            request_url = self.create_url()
            print("### generate ### request_url:", request_url)
            websocket.enableTrace(False)
            ws = websocket.WebSocketApp(
                request_url,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close,
                on_open=on_open,
            )

            ws.app_id = self.app_id
            ws.trace_id = "".join(random.choices(string.ascii_letters + string.digits, k=16))
            ws.content = text
            ws.assistant_code = self.assistant_code

            ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})

        # Start WebSocket connection in a separate thread
        Thread(target=websocket_thread).start()

        # Stream the response
        response = ""
        while True:
            chunk, is_final = message_queue.get()
            response += chunk
            yield response
            if is_final:
                break

def gen_params(trace_id, app_id, assistant_code, content):
    data = {
        "header": {
            "assistantCode": assistant_code,
            "traceId": trace_id,
            "appId": app_id,
        },
        "parameter": {
            "shortCircuitSetting": {
                "topN": 1,
                "thresholdScore": -1,
                "dbList": [
                    {"name": "db1", "version": 1},
                    {"name": "db2", "version": 1},
                ],
            },
            "docSearchSetting": {
                "topN": 5,
                "thresholdScore": -1,
                "dbList": [
                    {"name": "db1", "version": 1},
                    {"name": "db2", "version": 1},
                ],
            },
        },
        "payload": {"text": [{"content": content, "content_type": "text"}]},
    }
    return data

def create_gradio_interface():
    client = LLMClient(
        app_id="20241204AN155400ocba",
        secret="E1EF9E2901AF46929134AF752B6BB608",
        base_url="ws://10.54.69.27:32012/flames/api/v1/chat",
        assistant_code="base@1864208186935574528"  # 65B
    )

    # 使用Blocks来创建界面，而不是直接使用ChatInterface
    with gr.Blocks(
            title="讯飞65B大模型测试",
            css=css,
            head=get_custom_head(),
            theme=gr.themes.Soft()
    ) as iface:
        with gr.Column():
            gr.Markdown(
                """
                <div class="title-container">
                    <h1 style="display: inline;">讯飞65B大模型测试</h1>
                </div>
                """
            )

            chatbot = gr.ChatInterface(
                fn=client.chat,
                examples=["你好，请介绍一下你自己", "什么是快乐星球？", "总结一下《三体》的主要内容"]
            )

    return iface


if __name__ == "__main__":
    interface = create_gradio_interface()
    interface.launch(server_name="0.0.0.0")