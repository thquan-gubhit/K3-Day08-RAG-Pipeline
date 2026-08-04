"""
Task 5 — Semantic Search Module.

Viết module tìm kiếm ngữ nghĩa (dense retrieval) trên vector store.

Yêu cầu:
    - Input: query string + top_k
    - Output: danh sách chunks có score, sorted descending
    - Phải tương thích với embedding model và vector store ở Task 4
"""


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """
    Tìm kiếm ngữ nghĩa sử dụng vector similarity.

    Args:
        query: Câu truy vấn
        top_k: Số lượng kết quả tối đa

    Returns:
        List of {
            'content': str,      # Nội dung chunk
            'score': float,      # Cosine similarity score
            'metadata': dict     # source, doc_type, chunk_index
        }
        Sorted by score descending.
    """
    # TODO: Implement semantic search
    #
    # Bước 1: Embed query bằng cùng model ở Task 4
    # Bước 2: Query vector store (cosine similarity)
    # Bước 3: Return top_k results
    #
    # Ví dụ với ChromaDB:
    # from .task4_chunking_indexing import get_collection, get_embedding_model
    #
    # model = get_embedding_model()
    # query_vector = model.encode(query).tolist()
    #
    # collection = get_collection()
    # results = collection.query(
    #     query_embeddings=[query_vector],
    #     n_results=top_k,
    #     include=["documents", "metadatas", "distances"],
    # )
    #
    # output = []
    # for doc, meta, dist in zip(
    #     results["documents"][0], results["metadatas"][0], results["distances"][0]
    # ):
    #     score = max(0.0, 1.0 - dist)  # cosine distance → similarity
    #     output.append({"content": doc, "score": round(score, 4), "metadata": meta})
    #
    # output.sort(key=lambda x: x["score"], reverse=True)
    # return output[:top_k]
    if not query.strip() or top_k <= 0:
        return []

    from .task4_chunking_indexing import (
        CHROMA_DIR,
        COLLECTION_NAME,
        EMBEDDING_MODEL,
    )

    # Mở collection đã index ở Task 4. Nếu chưa chạy Task 4 (hoặc chưa cài
    # chromadb) thì trả list rỗng để Task 9 tự chuyển sang PageIndex fallback,
    # thay vì làm sập cả pipeline.
    try:
        import chromadb

        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        collection = client.get_collection(COLLECTION_NAME)
    except Exception:
        return []

    count = collection.count()
    if count == 0:
        return []

    # Query phải được embed bằng ĐÚNG model đã dùng lúc index (Task 4:
    # text-embedding-3-small, 1536 chiều) — lệch model là lệch số chiều vector
    # và ChromaDB sẽ báo lỗi dimension mismatch.
    import os

    from dotenv import load_dotenv

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return []

    from openai import OpenAI

    try:
        response = OpenAI(api_key=api_key).embeddings.create(
            model=EMBEDDING_MODEL, input=[query]
        )
        query_vector = response.data[0].embedding
    except Exception:
        return []

    raw = collection.query(
        query_embeddings=[query_vector],
        n_results=min(top_k, count),
        include=["documents", "metadatas", "distances"],
    )

    output = [
        {
            "content": doc,
            # Collection tạo với hnsw:space=cosine → distance = 1 - cosine.
            "score": max(0.0, 1.0 - float(distance)),
            "metadata": meta or {},
        }
        for doc, meta, distance in zip(
            raw["documents"][0], raw["metadatas"][0], raw["distances"][0]
        )
    ]
    output.sort(key=lambda item: item["score"], reverse=True)
    return output[:top_k]


if __name__ == "__main__":
    # Test
    results = semantic_search("what is the tuition fee", top_k=5)
    for r in results:
        print(f"[{r['score']:.3f}] {r['content'][:100]}...")
