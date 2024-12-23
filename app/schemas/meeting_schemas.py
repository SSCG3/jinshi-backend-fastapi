### backend/app/schemas/meeting_schemas.py
from pydantic import BaseModel
from typing import Optional, List

class GenerateMinutesRequest(BaseModel):
    transcription: str
    template: Optional[str] = None