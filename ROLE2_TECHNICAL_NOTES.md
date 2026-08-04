# Role 2 — Ghi chú trình bày kỹ thuật

## Dense Search

Dense Search dùng cùng một embedding model để biến câu hỏi và các document chunk
thành vector. ChromaDB tìm các vector chunk gần vector truy vấn nhất theo cosine
distance. Module Semantic Search chuyển distance thành similarity bằng `1 - distance`
và sắp xếp giảm dần.

## HyDE

HyDE không embed trực tiếp câu hỏi ngắn. LLM tạo một hypothetical document —
một đoạn trả lời giả định có ngôn ngữ gần với tài liệu chính sách. Hệ thống
embed đoạn giả định này rồi dùng vector đó để truy vấn ChromaDB. HyDE có thể
tăng recall khi câu hỏi và corpus dùng từ ngữ khác nhau; hypothetical document
chỉ dùng cho retrieval, không được coi là evidence để sinh câu trả lời.

## Lưu trữ ChromaDB

Task 4 đọc Markdown trong `data/standardized/`, chia chunk với `CHUNK_SIZE=800` và
`CHUNK_OVERLAP=100`, sau đó lưu vào collection `university_services_docs`:

- `ids`: `source::chunk_index`, duy nhất cho từng chunk;
- `documents`: nội dung chunk;
- `embeddings`: vector dense;
- `metadatas`: `source`, `type`, `path`, `chunk_index`, `customer_role`.

Collection dùng `hnsw:space = cosine` và được persist trong `chroma_db/`. Khi
corpus thay đổi, phải rebuild collection để tránh trộn chunk cũ với chunk mới.

## RRF và Retrieval Pipeline

Task 7 gộp các danh sách xếp hạng bằng `1 / (60 + rank)`. Task 9 chạy
Semantic Search và BM25, gộp hai list bằng RRF, lấy `top_k` và gắn
`item["source"] = "hybrid"`. Ngưỡng evidence phải so với cosine gốc của Dense
Search, không so với điểm RRF.
