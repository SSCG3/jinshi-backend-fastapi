### backend/app/schemas/email_schemas.py

from pydantic import BaseModel, EmailStr

class EmailRequest(BaseModel):
    to_email: EmailStr
    subject: str
    content: str
    sender_name: str
    receiver_name: str