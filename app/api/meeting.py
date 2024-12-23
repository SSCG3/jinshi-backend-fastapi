### backend/app/api/meeting.py
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from ..services.asr_meeting_model import ASRService
from ..services.meeting_general_llm import MeetingGeneralLLMService
from ..schemas.meeting_schemas import GenerateMinutesRequest
from fastapi import Body
import os
from datetime import datetime
import requests

router = APIRouter(prefix="/api", tags=["会议"])


@router.post("/meeting/upload")
async def upload_audio(file: UploadFile):
    # 生成新文件名
    _, ext = os.path.splitext(file.filename)
    new_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"

    # 构建请求
    files = {'file': (new_filename, await file.read(), 'audio/mpeg')}
    headers = {'Accept': 'application/json'}

    try:
        # 转发到目标服务器
        response = requests.post(
            "http://www.huidou123.com:9000/audio/upload",
            files=files,
            headers=headers
        )

        if response.status_code == 200:
            return JSONResponse({
                "filename": new_filename,
                "status": "success"
            })
        else:
            raise HTTPException(status_code=400, detail="Upload failed")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/meeting/transcribe")
async def transcribe_audio(filename: str = Body(..., embed=True)):
    try:
        asr_service = ASRService()
        return StreamingResponse(
            asr_service.transcribe_stream(filename),
            media_type='text/event-stream'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/meeting/generate-minutes")
async def generate_minutes(
        request: GenerateMinutesRequest,
        meeting_general_llm_service: MeetingGeneralLLMService = Depends()
):
    try:
        return StreamingResponse(
            meeting_general_llm_service.generate_stream(request.transcription),
            media_type='text/event-stream'
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
