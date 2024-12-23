### backend/app/services/email_services.py

import smtplib
from email.mime.text import MIMEText
from email.header import Header

class EmailService:
    def __init__(self):
        self.mail_host = "smtp.163.com"
        self.mail_user = "zhouquanxi01@163.com"
        self.mail_pass = "NYmTqBrLMM4qUpJ9"
        self.sender = "zhouquanxi01@163.com"

    async def send_email(self, to_email: str, subject: str, content: str,
                        sender_name: str, receiver_name: str) -> bool:
        message = MIMEText(content, 'plain', 'utf-8')
        message['From'] = Header(sender_name, 'utf-8')
        message['To'] = Header(receiver_name, 'utf-8')
        message['Subject'] = Header(subject, 'utf-8')

        try:
            smtp_obj = smtplib.SMTP()
            smtp_obj.connect(self.mail_host, 25)
            smtp_obj.login(self.mail_user, self.mail_pass)
            smtp_obj.sendmail(self.sender, [to_email], message.as_string())
            return True
        except Exception as e:
            print(f"Send email error: {str(e)}")
            return False