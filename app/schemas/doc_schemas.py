# backend/app/schemas/doc_schemas.py
from pydantic import BaseModel
from typing import List, Optional

class DocTemplate(BaseModel):
    title: str
    content: str
    template_type: str

class DocGenerateRequest(BaseModel):
    doc_type: str
    requirements: str
    reference_materials: Optional[List[str]] = []