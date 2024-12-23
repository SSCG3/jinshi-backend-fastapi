import gradio as gr
import json
import hmac
import hashlib
import base64
import random
import string
import ssl
import websocket
import time
from datetime import datetime
from time import mktime
from wsgiref.handlers import format_date_time
from urllib.parse import urlparse, urlencode
import queue
from queue import Queue
from threading import Thread
import os


from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# Load embeddings and vector store
EMBEDDING_MODEL = '/cs-root/projects/jinshi/backend/models/-bge-m3'
embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)



db = FAISS.load_local(
    '/cs-root/projects/jinshi/backend/database/faiss/smallData',
    embeddings,
    allow_dangerous_deserialization=True
)


class RAGEnhancedLLMClient:
    def __init__(self, app_id, secret, base_url, assistant_code, vector_store, k=3):
        self.app_id = app_id
        self.secret = secret
        self.assistant_code = assistant_code
        self.base_url = base_url
        self.vector_store = vector_store
        self.k = k
        self.timeout = 30  # 添加超时设置

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

    def get_relevant_context(self, query):
        docs = self.vector_store.similarity_search(query, k=self.k)
        context = "\n".join([f"相关文档 {i + 1}:\n{doc.page_content}\n"
                             for i, doc in enumerate(docs)])
        return context

    def chat(self, text, history):
        message_queue = Queue()
        context = self.get_relevant_context(text)
        augmented_prompt = f"""根据以下参考资料回答问题：

    参考资料：
    {context}

    用户问题：{text}

    回答："""

        def on_message(ws, message):
            data = json.loads(message)
            code = data["header"]["code"]
            if code != 0:
                ws.close()
            else:
                choices = data["payload"]["choices"]
                content = choices["text"][0]["content"]
                status = choices["status"]
                # 处理特殊字符
                content = content.replace("<ret>", "\n").replace("<end>", "")
                message_queue.put((content, status == 2))


        def on_error(ws, error):
            message_queue.put((f"连接错误: {str(error)}", True))

        def on_open(ws):
            data = json.dumps(
                gen_params(
                    trace_id=ws.trace_id,
                    app_id=ws.app_id,
                    assistant_code=ws.assistant_code,
                    content=augmented_prompt,
                )
            )
            ws.send(data)


        def websocket_thread():
            request_url = self.create_url()

            ws = websocket.WebSocketApp(
                request_url,
                on_message=on_message,
                on_error=on_error,
                on_open=on_open,
            )

            ws.app_id = self.app_id
            ws.trace_id = "".join(random.choices(string.ascii_letters + string.digits, k=16))
            ws.content = augmented_prompt
            ws.assistant_code = self.assistant_code

            ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})


        Thread(target=websocket_thread).start()

        response = ""
        start_time = time.time()
        while True:
            try:
                if time.time() - start_time > self.timeout:
                    yield "响应超时，请重试"
                    break

                chunk, is_final = message_queue.get(timeout=1.0)
                response += chunk
                # 确保每次yield都返回完整的response
                yield response.strip()
                if is_final:
                    break
            except queue.Empty:
                continue
            except Exception as e:
                yield f"处理响应时出错: {str(e)}"
                break


def gen_params(trace_id, app_id, assistant_code, content):
    return {
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

# 添加CSS样式
css = """
    footer {display: none !important}

    body {
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }
    
    #component-6 {
        position: relative !important;
        height: 500px !important;
        box-sizing: border-box !important;
        display: flex !important;
        flex-direction: column !important;
        padding: 10px !important;
    }

    .chat-interface {
        height: calc(200vh - 350px) !important;
        display: flex !important;
        flex-direction: column !important;
    }

    .title-container {
        padding: 10px 0 !important;
    }
"""

def create_gradio_interface():
    client = RAGEnhancedLLMClient(
        app_id="20241204AN155400ocba",
        secret="E1EF9E2901AF46929134AF752B6BB608",
        base_url="ws://10.54.69.27:32012/flames/api/v1/chat",
        assistant_code="base@1864208186935574528",
        vector_store=db
    )

    with gr.Blocks(title="讯飞65B大模型 RAG测试", css=css, head=get_custom_head(), theme=gr.themes.Soft()) as iface:
        with gr.Column():
            gr.Markdown("""### 讯飞65B大模型 RAG测试""")

            # 使用正确的参数配置ChatInterface
            chatbot = gr.ChatInterface(
                fn=client.chat,
                textbox=gr.Textbox(placeholder="请输入您的问题...", container=False, scale=17),
                examples=[
                    "你好，请介绍一下国能集团。",
                    "请说一下国能集团最近发生了哪些事情？",
                    "请介绍一下国能集团比较重要的事件"
                ]
            )

    return iface


if __name__ == "__main__":
    interface = create_gradio_interface()
    interface.launch(server_name="0.0.0.0")