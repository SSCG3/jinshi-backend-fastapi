# backend/app/api/rag.py

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from ..services.rag_service import RAGService
from pydantic import BaseModel
import json

router = APIRouter(prefix="/api", tags=["RAG对话"])


class ChatRequest(BaseModel):
    query: str


@router.post("/rag/chat")
async def chat(
        request: ChatRequest,
        rag_service: RAGService = Depends()
):
    async def generate():
        async for chunk in rag_service.chat_stream(request.query):
            yield f"data: {json.dumps({'content': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream"
    )