# backend/fastapi/main.py
from dotenv import load_dotenv
load_dotenv()  # 这会加载 .env 文件中的环境变量
from app import app

@app.get("/")
def read_root():
    return {"message": "Hello World"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=3030)