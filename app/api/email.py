### backend/app/api/email.py
from fastapi import APIRouter, HTTPException, Depends
from ..schemas.email_schemas import EmailRequest
from ..services.email_service import EmailService

router = APIRouter(prefix="/api", tags=["邮件服务"])


@router.post("/send-email")
async def send_email(
        request: EmailRequest,
        email_service: EmailService = Depends()
):
    try:
        success = await email_service.send_email(
            to_email=request.to_email,
            subject=request.subject,
            content=request.content,
            sender_name=request.sender_name,
            receiver_name=request.receiver_name
        )

        if success:
            return {"message": "邮件发送成功"}
        else:
            raise HTTPException(status_code=500, detail="邮件发送失败")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))