### backend/app/schemas/__init__.py
from .doc_schemas import DocTemplate, DocGenerateRequest
from .email_schemas import EmailRequest
from .meeting_schemas import GenerateMinutesRequest

__all__ = ['DocTemplate', 'DocGenerateRequest', 'EmailRequest', 'GenerateMinutesRequest']
