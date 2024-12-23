# backend/app/services/rag_service.py

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
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS


class RAGService:
    def __init__(self):
        # 初始化embeddings和向量存储
        EMBEDDING_MODEL = './models/-bge-m3'
        self.embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
        self.vector_store = FAISS.load_local(
            './database/faiss/smallData',
            self.embeddings,
            allow_dangerous_deserialization=True
        )

        # LLM配置
        self.app_id = "20241204AN155400ocba"
        self.secret = "E1EF9E2901AF46929134AF752B6BB608"
        self.base_url = "ws://10.54.69.27:32012/flames/api/v1/chat"
        self.assistant_code = "base@1864208186935574528"
        self.k = 3
        self.timeout = 30

        parsed = urlparse(self.base_url)
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
            digestmod=hashlib.sha256
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

        return self.base_url + "?" + urlencode(v)

    def get_relevant_context(self, query):
        docs = self.vector_store.similarity_search(query, k=self.k)
        context = "\n".join([f"相关文档 {i + 1}:\n{doc.page_content}\n"
                             for i, doc in enumerate(docs)])
        return context

    def gen_params(self, trace_id, content):
        return {
            "header": {
                "assistantCode": self.assistant_code,
                "traceId": trace_id,
                "appId": self.app_id,
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

    async def chat_stream(self, query):
        message_queue = Queue()
        context = self.get_relevant_context(query)
        augmented_prompt = f"""根据以下参考资料回答问题：

参考资料：
{context}

用户问题：{query}

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
                self.gen_params(
                    trace_id=ws.trace_id,
                    content=augmented_prompt
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
                    yield "响应超时，请重试\n"
                    break

                chunk, is_final = message_queue.get(timeout=1.0)
                response += chunk
                # 确保每次yield都返回完整的response
                yield response.strip() + "\n"
                if is_final:
                    break
            except queue.Empty:
                continue
            except Exception as e:
                yield f"处理响应时出错: {str(e)}\n"
                break