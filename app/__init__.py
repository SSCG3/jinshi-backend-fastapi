# backend/app/__init__.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .api import doc_router, email_router, meeting_router, rag_router

app = FastAPI(title="金石系统API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册所有路由
app.include_router(doc_router)
app.include_router(email_router)
app.include_router(meeting_router)
app.include_router(rag_router)  # 添加新的RAG路由