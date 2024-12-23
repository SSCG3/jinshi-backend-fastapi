### backend/app/api/__init__.py

from .doc_writing import router as doc_router
from .email import router as email_router
from .meeting import router as meeting_router
from .rag import router as rag_router

__all__ = ['doc_router', 'email_router', 'meeting_router', 'rag_router']