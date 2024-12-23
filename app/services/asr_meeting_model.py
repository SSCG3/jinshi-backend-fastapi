### backend/app/services/asr_meeting_model.py
from aliyunsdkcore.client import AcsClient
from aliyunsdkcore.request import CommonRequest
import asyncio
import json
from dotenv import load_dotenv
import os


class ASRService:
    def __init__(self):
        # 加载环境变量
        load_dotenv()

        self.access_key_id = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID')
        self.access_key_secret = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET')
        self.app_key = os.getenv('ALIBABA_CLOUD_APP_KEY')

        self.client = AcsClient(
            self.access_key_id,
            self.access_key_secret,
            "cn-shanghai"
        )

    async def transcribe_stream(self, filename: str):
        """流式转写音频文件"""
        file_link = f"http://www.huidou123.com:9000/audio/{filename}"
        task_id = self._submit_task(file_link)
        if not task_id:
            yield f"data: {json.dumps({'error': '提交转写任务失败'})}\n\n"
            return

        while True:
            status, result = self._get_task_result(task_id)
            if status == "SUCCESS":
                # 按句子分块输出
                sentences = result["Sentences"]
                for sentence in sentences:
                    yield f"data: {json.dumps({'content': sentence['Text'] + ' '})}\n\n"
                    await asyncio.sleep(0.1)  # 控制输出速度
                break
            elif status in ["RUNNING", "QUEUEING"]:
                yield f"data: {json.dumps({'content': '转写中...'})}\n\n"
                await asyncio.sleep(3)
                continue
            else:
                yield f"data: {json.dumps({'error': f'转写失败: {status}'})}\n\n"
                break

        yield "data: [DONE]\n\n"

    def _submit_task(self, file_link: str) -> str:
        request = CommonRequest()
        request.set_domain('filetrans.cn-shanghai.aliyuncs.com')
        request.set_version('2018-08-17')
        request.set_product('nls-filetrans')
        request.set_action_name('SubmitTask')
        request.set_method('POST')

        task = {
            "appkey": self.app_key,
            "file_link": file_link,
            "version": "4.0",
            "enable_words": False,
            "enable_sample_rate_adaptive": True
        }
        request.add_body_params("Task", json.dumps(task))

        try:
            response = json.loads(self.client.do_action_with_exception(request))
            return response["TaskId"]
        except Exception as e:
            print(f"Submit task error: {e}")
            return None

    def _get_task_result(self, task_id: str):
        request = CommonRequest()
        request.set_domain('filetrans.cn-shanghai.aliyuncs.com')
        request.set_version('2018-08-17')
        request.set_product('nls-filetrans')
        request.set_action_name('GetTaskResult')
        request.set_method('GET')
        request.add_query_param("TaskId", task_id)

        try:
            response = json.loads(self.client.do_action_with_exception(request))
            status = response["StatusText"]
            return status, response.get("Result")
        except Exception as e:
            print(f"Get result error: {e}")
            return "FAILED", None