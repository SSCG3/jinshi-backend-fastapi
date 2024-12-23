from langchain_community.document_loaders import UnstructuredFileLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore
from langchain_community.docstore.document import Document
import numpy as np
import faiss
from typing import List


class ProgressHuggingFaceEmbeddings(HuggingFaceEmbeddings):
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        total = len(texts)
        for i, text in enumerate(texts, 1):
            embedding = super().embed_documents([text])[0]
            embeddings.append(embedding)
            if i % 50 == 0:
                print(f"向量化进度: {i}/{total} ({(i / total * 100):.1f}%)")
        return embeddings


def main():
    EMBEDDING_MODEL = '/cs-root/projects/jinshi/backend/models/-bge-m3'
    print("开始加载文件...")
    loader = UnstructuredFileLoader('/cs-root/projects/jinshi/backend/data/smallData.txt')
    data = loader.load()

    print(f"文件加载完成，开始分割...")
    text_split = RecursiveCharacterTextSplitter(chunk_size=256, chunk_overlap=38)
    split_data = text_split.split_documents(data)
    print(f"分割完成,共 {len(split_data)} 个片段")

    embeddings = ProgressHuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    texts = [doc.page_content for doc in split_data]

    print("开始生成向量embeddings...")
    embeddings_list = embeddings.embed_documents(texts)
    print("Embedding完成，开始构建FAISS索引...")

    embeddings_array = np.array(embeddings_list).astype('float32')
    dimension = embeddings_array.shape[1]
    index = faiss.IndexFlatL2(dimension)

    print(f"正在向FAISS添加 {len(embeddings_array)} 个向量...")
    batch_size = 500
    for i in range(0, len(embeddings_array), batch_size):
        batch_end = min(i + batch_size, len(embeddings_array))
        batch = embeddings_array[i:batch_end]
        index.add(batch)
        print(
            f"FAISS索引构建进度: {batch_end}/{len(embeddings_array)} ({(batch_end / len(embeddings_array) * 100):.1f}%)")

    # 创建docstore和文档ID映射
    docstore = InMemoryDocstore({})
    doc_ids = {}
    for i, text in enumerate(texts):
        doc_id = str(i)
        doc = Document(page_content=text)
        docstore.add({doc_id: doc})
        doc_ids[i] = doc_id

    # 创建FAISS包装器
    db = FAISS(
        embeddings.embed_query,
        index,
        docstore,
        doc_ids
    )

    print("索引构建完成,正在保存...")
    db.save_local('/cs-root/projects/jinshi/backend/database/faiss/smallData')
    print("全部完成!")
    return split_data


if __name__ == '__main__':
    split_data = main()