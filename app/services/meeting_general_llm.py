### backend/app/services/meeting_general_llm.py
import qianfan
import os
import json
import re

class MeetingGeneralLLMService:
    def __init__(self):
        self.ak = os.getenv('QIANFAN_AK')
        self.sk = os.getenv('QIANFAN_SK')
        self.chat_comp = qianfan.ChatCompletion()

    def generate_stream(self, transcription: str):
        messages = [{
            "role": "user",
            "content": self._build_prompt_2(transcription)
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
                            # print("===Result===", result)
                            yield f"data: {json.dumps({'content': result})}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            print("Error:", e)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"


    def _build_prompt_2(self, requirements: str) -> str:
        return f"""你是一个专业的会议纪要撰写助手。请根据以下会议音频转写的文本内容，按照会议纪要要求，生成一份完整的会议纪要。:
        音频转写内容：
        {requirements}
        -------------
        会议纪要要求:
        1.不需要生成'会议纪要'这几个字，不需要生成'会议时间'、'会议地点'和'备注'。
        2.直接生成会议主题、会议目的、会议概要、讨论内容、跟进事项和会议总结这几块儿内容。
        -------------
        请按照会议纪要要求的两点要求，根据音频转写的内容，生成一份专业、简洁、准确的会议纪要。
        """