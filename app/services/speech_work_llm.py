### backend/app/services/speech_work_llm.py
import qianfan
import os
import json
import re

class SpeechWorkLLMService:
    def __init__(self):
        self.ak = os.getenv('QIANFAN_AK')
        self.sk = os.getenv('QIANFAN_SK')
        self.chat_comp = qianfan.ChatCompletion()

    def generate_doc_stream(self, requirements: str):
        messages = [{
            "role": "user",
            "content": self._build_prompt(requirements)
        }]

        try:
            response = self.chat_comp.do(
                model="ERNIE-Bot-4",
                messages=messages,
                stream=True,
                temperature=0.7,
                top_p=0.8
            )

            for chunk in response:
                if chunk:
                    # 直接获取result字段的内容
                    content = chunk.result if hasattr(chunk, 'result') else str(chunk)
                    if content:
                        # Use regular expression to find the 'result' value
                        match = re.search(r"'result':\s*'([^']*)'", content)

                        if match:
                            result = match.group(1)
                            #print("===Result===", result)
                            yield f"data: {json.dumps({'content': result})}\n\n"



            yield "data: [DONE]\n\n"

        except Exception as e:
            print("Error:", e)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    def _build_prompt(self, requirements: str) -> str:
        return f"""请根据以下要求生成一份工作会议讲话稿:
        {requirements}
        
        要求:
        1. 语言严谨规范,符合讲话稿风格
        2. 结构清晰,层次分明
        3. 内容积极向上,富有激励性
        4. 直接输出稿件正文，不需要输出大标题
        """