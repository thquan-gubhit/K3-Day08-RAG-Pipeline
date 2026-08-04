# Checkpoint 6 — Giải thích kỹ thuật Dense Search và HyDE

Tài liệu này mô tả đúng cấu hình đang dùng trong `src/task4_chunking_indexing.py`
và cách Dense Search/HyDE kết nối với ChromaDB.

## 1. Dense Search hoạt động như thế nào?

Dense Search tìm theo **ý nghĩa**, không yêu cầu câu hỏi và tài liệu phải chứa đúng
cùng từ khóa. Cả document chunk và câu hỏi đều được đưa qua **cùng một embedding
model** để tạo vector trong cùng không gian ngữ nghĩa.

Luồng xử lý:

1. Task 4 chia tài liệu thành các chunk.
2. Mỗi chunk được OpenAI `text-embedding-3-small` mã hóa thành vector 1536 chiều.
3. Vector, nội dung và metadata của chunk được lưu vào ChromaDB.
4. Khi có câu hỏi, Task 5 phải mã hóa câu hỏi bằng đúng model
   `text-embedding-3-small`.
5. ChromaDB so sánh vector câu hỏi với vector của các chunk bằng cosine distance và
   trả về `top_k` chunk gần nhất.
6. Pipeline đổi distance thành similarity bằng `score = 1 - distance`, rồi sắp xếp
   giảm dần. Score càng gần 1 thì nội dung càng gần nghĩa với câu hỏi.

Ví dụ: câu hỏi “Gửi sản phẩm lại như thế nào?” vẫn có thể tìm được chunk mang tiêu
đề “Quy trình trả hàng/hoàn tiền”, dù hai câu không dùng hoàn toàn cùng từ ngữ.

Dense Search bổ sung cho BM25: Dense Search mạnh về đồng nghĩa/ngữ cảnh, còn BM25
mạnh với từ khóa chính xác như mã voucher, mã sản phẩm hoặc tên điều khoản.

## 2. HyDE: embed hypothetical document

HyDE (Hypothetical Document Embeddings) không embed trực tiếp câu hỏi ngắn. Nó nhờ
LLM viết một **đoạn trả lời giả định** có văn phong gần với tài liệu trong corpus,
sau đó embed đoạn giả định đó để tìm kiếm.

Luồng HyDE:

```text
Câu hỏi
  → LLM tạo hypothetical document
  → embed hypothetical document bằng text-embedding-3-small
  → query ChromaDB bằng vector vừa tạo
  → lấy các chunk thật làm evidence
```

Ví dụ:

```text
Query: "Shop hoàn tiền bao lâu?"

Hypothetical document:
"Thời gian hoàn tiền phụ thuộc vào phương thức thanh toán và được xử lý sau khi
yêu cầu trả hàng/hoàn tiền được chấp thuận..."
```

Đoạn giả định thường chứa nhiều thuật ngữ giống văn bản chính sách hơn câu hỏi ban
đầu, vì vậy có thể tăng recall khi cách diễn đạt của người dùng khác corpus.

Điểm quan trọng:

- Hypothetical document chỉ là **truy vấn mở rộng**, không phải nguồn sự thật.
- Không được đưa nội dung giả định vào citation hoặc dùng nó làm evidence cuối cùng.
- Câu trả lời cuối chỉ được sinh từ các chunk thật lấy ra từ ChromaDB.
- HyDE tốn thêm một lần gọi LLM và có thể làm truy vấn lệch hướng; nên so sánh kết
  quả với Dense Search trực tiếp và dùng RRF nếu cần gộp hai danh sách.

Trong repository hiện tại, `src/task5_semantic_search.py` vẫn là starter và chưa có
code HyDE. Checkpoint 6 yêu cầu giải thích cơ chế; muốn chạy HyDE thực tế thì thành
viên phụ trách Task 5 phải triển khai bước tạo hypothetical document và truy vấn
vector store.

## 3. ChromaDB lưu dữ liệu như thế nào?

Task 4 dùng `chromadb.PersistentClient`, vì vậy index được ghi xuống ổ đĩa tại:

```text
K3-Day08-RAG-Pipeline/chroma_db/
```

Collection đang dùng:

```text
university_services_docs
```

Collection được cấu hình `hnsw:space = cosine`. Với mỗi chunk, ChromaDB lưu bốn
thành phần:

| Thành phần | Giá trị trong Task 4 | Mục đích |
|---|---|---|
| `id` | `source::chunk_<chunk_index>` | Định danh duy nhất của chunk |
| `document` | Nội dung chunk | Evidence trả về cho RAG |
| `embedding` | Vector 1536 chiều | Tìm kiếm cosine |
| `metadata` | `source`, `type`, `chunk_index` | Hiển thị nguồn, lọc và citation |

Pipeline tạo index thực tế:

```text
data/standardized/**/*.md
  → load_documents()
  → chunk_documents(size=800, overlap=100)
  → embed_chunks(text-embedding-3-small, 1536 chiều)
  → index_to_vectorstore()
  → chroma_db/university_services_docs
```

Overlap 100 ký tự giữ lại một phần ngữ cảnh ở ranh giới hai chunk, giúp câu hoặc ý
không bị cắt rời hoàn toàn. Khi index, Task 4 xóa collection cùng tên rồi tạo lại;
điều này ngăn dữ liệu cũ bị trộn với corpus mới.

## 4. Nội dung trình bày ngắn trong demo

> Dense Search biến câu hỏi và các chunk thành vector bằng cùng model, sau đó dùng
> cosine để tìm những chunk gần nghĩa nhất. HyDE cải thiện truy vấn bằng cách cho
> LLM tạo một đoạn trả lời giả định rồi embed đoạn đó; đoạn giả định chỉ dùng để
> search, không bao giờ được coi là evidence. ChromaDB lưu persistent tại
> `chroma_db/`, trong collection `university_services_docs`, gồm ID, nội dung,
> embedding 1536 chiều và metadata nguồn cho từng chunk.

## 5. Checklist Checkpoint 6

- [x] Giải thích cơ chế Dense Search và cosine similarity.
- [x] Giải thích cách embed hypothetical document trong HyDE.
- [x] Phân biệt hypothetical document với evidence thật.
- [x] Trình bày đường dẫn, collection và cấu trúc dữ liệu ChromaDB.
- [x] Nêu đúng chunk size 800, overlap 100 và embedding 1536 chiều.
