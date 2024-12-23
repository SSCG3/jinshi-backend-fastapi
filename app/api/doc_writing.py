# backend/app/api/doc_writing.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from ..schemas.doc_schemas import DocTemplate, DocGenerateRequest
from ..services.speech_work_llm import SpeechWorkLLMService
from pydantic import ValidationError

router = APIRouter(prefix="/api", tags=["文稿写作"])

@router.post("/generate-doc")
async def generate_doc(
    request: DocGenerateRequest,
    speech_work_service: SpeechWorkLLMService = Depends()
):
    try:
        return StreamingResponse(
            speech_work_service.generate_doc_stream(request.requirements),
            media_type='text/event-stream'
        )
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
