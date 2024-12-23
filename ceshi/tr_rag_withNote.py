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
import logging

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# Load embeddings and vector store
EMBEDDING_MODEL = '/cs-root/projects/jinshi/backend/models/-bge-m3'
logger.info(f"Loading embedding model from: {EMBEDDING_MODEL}")

try:
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    logger.info("Embedding model loaded successfully")
except Exception as e:
    logger.error(f"Error loading embedding model: {e}")
    raise

try:
    db = FAISS.load_local(
        '/cs-root/projects/jinshi/backend/database/faiss/smallData',
        embeddings,
        allow_dangerous_deserialization=True
    )
    logger.info("FAISS database loaded successfully")
except Exception as e:
    logger.error(f"Error loading FAISS database: {e}")
    raise


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
        logger.info(f"Initialized RAG client with host: {self.host}, path: {self.path}")

    def create_url(self):
        try:
            now = datetime.now()
            date = format_date_time(mktime(now.timetuple()))

            signature_origin = f"host: {self.host}\n"
            signature_origin += f"date: {date}\n"
            signature_origin += f"GET {self.path} HTTP/1.1"

            logger.debug(f"Signature origin: {signature_origin}")

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
            logger.info(f"Created WebSocket URL: {url}")
            return url
        except Exception as e:
            logger.error(f"Error creating URL: {e}")
            raise

    def get_relevant_context(self, query):
        logger.info(f"Getting relevant context for query: {query}")
        start_time = time.time()

        try:
            docs = self.vector_store.similarity_search(query, k=self.k)
            logger.info(f"Found {len(docs)} relevant documents")

            context = "\n".join([f"相关文档 {i + 1}:\n{doc.page_content}\n"
                                 for i, doc in enumerate(docs)])

            logger.debug(f"Retrieved context: {context}")

            end_time = time.time()
            logger.info(f"Context retrieval took {end_time - start_time:.2f} seconds")

            return context
        except Exception as e:
            logger.error(f"Error retrieving context: {e}")
            return f"Error retrieving context: {str(e)}"

    def chat(self, text, history):
        message_queue = Queue()
        context = self.get_relevant_context(text)
        augmented_prompt = f"""根据以下参考资料回答问题：

    参考资料：
    {context}

    用户问题：{text}

    回答："""

        def on_message(ws, message):
            try:
                data = json.loads(message)
                code = data["header"]["code"]
                if code != 0:
                    logger.error(f"Request error: {code}, {data}")
                    ws.close()
                else:
                    choices = data["payload"]["choices"]
                    content = choices["text"][0]["content"]
                    status = choices["status"]
                    # 处理特殊字符
                    content = content.replace("<ret>", "\n").replace("<end>", "")
                    message_queue.put((content, status == 2))
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                message_queue.put((f"Error processing message: {str(e)}", True))

        def on_error(ws, error):
            logger.error(f"WebSocket error: {error}")
            message_queue.put((f"连接错误: {str(error)}", True))

        def on_close(ws, close_status_code, close_msg):
            logger.info(f"WebSocket closed: code={close_status_code}, msg={close_msg}")

        def on_open(ws):
            logger.info("WebSocket connection opened")
            try:
                data = json.dumps(
                    gen_params(
                        trace_id=ws.trace_id,
                        app_id=ws.app_id,
                        assistant_code=ws.assistant_code,
                        content=augmented_prompt,
                    )
                )
                logger.debug(f"Sending data: {data}")
                ws.send(data)
            except Exception as e:
                logger.error(f"Error sending data: {e}")
                message_queue.put((f"发送数据错误: {str(e)}", True))

        def websocket_thread():
            try:
                request_url = self.create_url()
                logger.info(f"Connecting to URL: {request_url}")

                ws = websocket.WebSocketApp(
                    request_url,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close,
                    on_open=on_open,
                )

                ws.app_id = self.app_id
                ws.trace_id = "".join(random.choices(string.ascii_letters + string.digits, k=16))
                ws.content = augmented_prompt
                ws.assistant_code = self.assistant_code

                ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE})
            except Exception as e:
                logger.error(f"WebSocket thread error: {e}")
                message_queue.put((f"WebSocket连接错误: {str(e)}", True))

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
                logger.error(f"Error processing response: {e}")
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


def create_gradio_interface():
    logger.info("Creating Gradio interface")

    client = RAGEnhancedLLMClient(
        app_id="20241204AN155400ocba",
        secret="E1EF9E2901AF46929134AF752B6BB608",
        base_url="ws://10.54.69.27:32012/flames/api/v1/chat",
        assistant_code="base@1864208186935574528",
        vector_store=db
    )

    with gr.Blocks(title="讯飞65B大模型 RAG测试") as iface:
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
    logger.info("Starting application")
    interface = create_gradio_interface()
    interface.launch(server_name="0.0.0.0")