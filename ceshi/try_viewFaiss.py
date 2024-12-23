import re
import os
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores.faiss import FAISS


def check_faiss_database():
    # 定义路径
    EMBEDDING_MODEL = '/opt/projects/jinshi/backend/fastapi/models/-bge-m3'
    FAISS_PATH = '/opt/projects/jinshi/backend/fastapi/database/faiss/smallData'

    # 检查文件路径
    print("检查FAISS文件路径:")
    print(f"FAISS路径是否存在: {os.path.exists(FAISS_PATH)}")
    if os.path.exists(FAISS_PATH):
        print(f"目录内容: {os.listdir(FAISS_PATH)}")

    # 加载embeddings模型
    print("\n加载Embeddings模型...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    # 加载FAISS数据库
    print("\n加载FAISS数据库...")
    try:
        db = FAISS.load_local(FAISS_PATH, embeddings, allow_dangerous_deserialization=True)

        # 检查数据库内容
        ids = len(db.index_to_docstore_id)
        print(f"\n数据库基本信息:")
        print(f"文档数量: {ids}")
        print(f"索引到文档ID的映射: {db.index_to_docstore_id}")

        # 如果数据库不为空，则提取内容
        if ids > 0:
            print("\n提取所有文档内容:")
            text = ""
            for i in range(ids):
                doc_id = db.index_to_docstore_id[i]
                doc = db.docstore.search(doc_id)
                if doc:
                    temp = doc.page_content
                    one_line_text = re.sub(r'\n', ' ', temp)
                    text += f"---文档 {i + 1}---\n{one_line_text}\n"
            print(text)
        else:
            print("\n数据库为空，没有文档内容")

    except Exception as e:
        print(f"错误: {str(e)}")
        print("\n请检查：")
        print("1. 数据库是否正确创建")
        print("2. 是否已经向数据库中添加了文档")
        print("3. 数据库文件是否完整")


if __name__ == "__main__":
    check_faiss_database()