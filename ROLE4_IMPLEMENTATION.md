# Role 4 — Frontend & Chatbot Developer · Tài liệu bàn giao

**Thành viên:** Nguyễn Quang Hưng (2A202601523)
**Phạm vi:** Task 10 (Generation có Citation) + Chatbot Streamlit `app.py` + giao diện React custom component.

---

## 1. Phạm vi Role 4

| # | Hạng mục | Trạng thái |
|---|----------|-----------|
| 1 | Hoàn thiện `src/task10_generation.py` | ✅ |
| 2 | Chatbot Streamlit trong `app.py` | ✅ |
| 3 | Tích hợp Retrieval Pipeline từ `src/task9_retrieval_pipeline.py` | ✅ |
| 4 | Hiển thị câu trả lời có citation `[Nguồn, Năm]` | ✅ |
| 5 | Hiển thị chính xác source documents đã dùng | ✅ |
| 6 | Follow-up question + conversation memory | ✅ |
| 7 | UI/UX chất lượng cao (React + Motion + Three.js) | ✅ |
| 8 | Ứng dụng ổn định cho live demo (có fallback native) | ✅ |
| 9 | Chạy test, không phá code thành viên khác | ✅ 35/35 pass |

**Không thuộc Role 4:** Task 1–9. Các file đó **không bị sửa** trong lần bàn giao này
(kiểm chứng bằng `git diff --stat`). Task 8 (PageIndex) thuộc Role 3 — Role 4 chỉ
tích hợp và hiển thị rõ khi pipeline chuyển sang fallback.

---

## 2. Các file đã tạo / sửa

### Sửa
| File | Nội dung |
|------|----------|
| `src/task10_generation.py` | Viết lại hoàn chỉnh, **giữ nguyên** signature 3 hàm mà test dùng |
| `app.py` | Viết lại: session state, luồng xử lý, source inspector, pipeline trace, error handling, 2 chế độ giao diện |
| `requirements.txt` | Thêm ghi chú về Custom Component (không thêm dependency Python mới) |
| `.gitignore` | Thêm rule Node/Vite; **cố ý KHÔNG ignore `dist/`** |

### Tạo mới
| File | Vai trò |
|------|---------|
| `src/role4_chat_service.py` | **Adapter** ghép Task 9 + Task 10: pipeline trace thật, system status, conversation memory, export |
| `components/__init__.py` | Package component |
| `components/university_chat_ui/__init__.py` | Python wrapper `declare_component()` |
| `components/university_chat_ui/frontend/**` | React + TypeScript + Vite + Tailwind + Motion + Three.js |
| `ROLE4_IMPLEMENTATION.md` | Tài liệu này |

> `src/role4_chat_service.py` là file **mới**, không đụng vào module của ai. Đặt tên
> có tiền tố `role4_` để tránh trùng tên với file thành viên khác tạo sau này.

---

## 3. Kiến trúc

```
streamlit run app.py
        │
        ├── st.session_state ── messages · conversation_id · top_k · last_sources
        │                       last_pipeline_trace · is_generating · ui_mode
        │
        ├── src/role4_chat_service.answer_question()
        │       │
        │       ├── resolve_follow_up()        ← conversation memory (deterministic)
        │       ├── _instrumented_retrieve()   ← đo thời gian THẬT từng chặng
        │       │       └── src/task9_retrieval_pipeline.retrieve()
        │       │               ├── task5 semantic_search   (ChromaDB, cosine)
        │       │               ├── task6 lexical_search    (BM25)
        │       │               ├── task7 rerank_rrf        (k=60)
        │       │               └── task8 pageindex_search  (fallback khi cosine < 0.48)
        │       │
        │       ├── src/task10_generation.generate_with_citation()
        │       │       ├── reorder_for_llm()   front + back[::-1]
        │       │       ├── format_context()    + sanitize chống prompt injection
        │       │       └── OpenRouter / OpenAI (temperature 0.1, top_p 0.2)
        │       │
        │       └── validate_citations()        ← đối chiếu citation với nguồn thật
        │
        └── Giao diện (2 chế độ, tự chọn)
                ├── components/university_chat_ui  ← React 18 + TS + Vite
                │       ├── Tailwind CSS (design tokens)
                │       ├── Motion for React (motion/react)
                │       ├── Three.js + @react-three/fiber 8.x → KnowledgeOrb
                │       └── lucide-react · react-markdown · remark-gfm · zod
                │
                └── Streamlit native (fallback bắt buộc, luôn khả dụng)
```

**Phân chia trách nhiệm** — Python giữ toàn bộ logic (retrieval, LLM, session state,
API key, metadata nguồn, latency, xử lý lỗi). React **chỉ** trình bày và gửi sự kiện.

### Giao thức sự kiện React → Python

React gửi `{ ...event, nonce: <uuid> }` qua `Streamlit.setComponentValue()`.
Python lưu `last_event_nonce`; nonce trùng thì bỏ qua.

> **Vì sao bắt buộc có nonce:** Streamlit trả lại *giá trị component cũ* ở **mọi**
> lần rerun sau đó. Không so nonce ⇒ một lần submit sẽ được xử lý lặp vô hạn.

Sự kiện hỗ trợ: `submit_query`, `select_suggestion`, `new_conversation`,
`clear_history`, `update_settings`, `select_source`. Sự kiện lạ bị bỏ qua an toàn.

---

## 4. Cách chạy

### 4.1 Chạy ứng dụng (đã có sẵn `dist/` trong repo)

```bash
pip install -r requirements.txt
streamlit run app.py
```

Chạy headless (máy không mở được browser):

```bash
streamlit run app.py --server.headless true
```

### 4.2 Build lại React component

```bash
cd components/university_chat_ui/frontend
npm install
npm run build
```

> Lưu ý: đường dẫn là `components/university_chat_ui/frontend`, **không phải**
> `university_chat_ui/frontend`.

Build xong sinh ra `components/university_chat_ui/frontend/dist/`. Quay lại thư mục
gốc và chạy `streamlit run app.py`.

Kiểm tra type (lint):

```bash
npm run lint
```

### 4.3 Chế độ dev cho frontend (hot reload)

```bash
cd components/university_chat_ui/frontend
npm run dev
```

Terminal khác, tại thư mục gốc:

```bash
UNIVERSITY_CHAT_UI_DEV=1 streamlit run app.py
```

PowerShell:

```bash
$env:UNIVERSITY_CHAT_UI_DEV="1"; streamlit run app.py
```

### 4.4 Chuyển giao diện

Sidebar → **Thiết lập** → **Giao diện**:
- `auto` — dùng React nếu đã build, ngược lại native (mặc định)
- `react` — ép dùng React
- `native` — ép dùng Streamlit native

---

## 5. Biến môi trường

Tạo `.env` ở thư mục gốc (copy từ `.env.example`). **Không commit `.env`.**

| Biến | Bắt buộc | Ghi chú |
|------|----------|---------|
| `OPENROUTER_API_KEY` | ★ (1 trong 2) | Ưu tiên dùng — có model `:free` |
| `OPENROUTER_MODEL` | không | Mặc định `openai/gpt-4o-mini` |
| `OPENAI_API_KEY` | ★ (1 trong 2) | Fallback khi không có OpenRouter |
| `OPENAI_MODEL` | không | Mặc định `gpt-4o-mini` |
| `PAGEINDEX_API_KEY` | không | Thiếu key → Task 8 chạy chế độ vectorless local |
| `UNIVERSITY_CHAT_UI_DEV` | không | `1` để trỏ component sang Vite dev server |
| `UNIVERSITY_CHAT_UI_DEV_URL` | không | Mặc định `http://localhost:5173` |

**Thiếu API key thì app KHÔNG crash:** retrieval + source inspector + pipeline trace
vẫn chạy đầy đủ; phần sinh câu trả lời trả về thông báo có kiểm soát kèm hướng dẫn
tạo `.env`. Giá trị key không bao giờ được log hay hiển thị.

---

## 6. Task 10 — chi tiết kỹ thuật

### 6.1 Signature được giữ nguyên

```python
def reorder_for_llm(chunks: list[dict]) -> list[dict]: ...
def format_context(chunks: list[dict]) -> str: ...
def generate_with_citation(query, context_chunks=None, top_k=5,
                           conversation_history=None, retrieve_fn=None) -> dict: ...
```

> **Khác biệt giữa đề bài và test — đã xử lý:**
> Đề bài mô tả `generate_with_citation(query, context_chunks) -> str`, nhưng
> `tests/test_individual.py:551` gọi `generate("...")` với **1 tham số** và assert
> `result` là **dict** có key `answer`. Theo quy tắc "ưu tiên test pass", hàm giữ
> kiểu trả về `dict` (giống bản gốc trong repo) và nhận thêm `context_chunks` như
> tham số **optional thứ 2** — nên cả hai kiểu gọi đều hợp lệ, và mọi call site cũ
> (`app.py`, `eval_pipeline.py`) không phải sửa.

### 6.2 Document reordering

`chunks[::2] + chunks[1::2][::-1]` → `[1,2,3,4,5]` thành `[1,3,5,4,2]`.

Đã kiểm chứng: list rỗng, 1/2/3/4/5/6 phần tử, **không mutate input**, giữ nguyên
metadata / score / kiểu dữ liệu chunk.

### 6.3 Tham số generation

| Tham số | Giá trị | Lý do |
|---------|---------|-------|
| `top_k` | 5 | Đủ nguồn tổng hợp; >8 làm tăng trích dẫn nhầm nguồn |
| `temperature` | 0.1 | Câu trả lời chính sách cần tái lập được giữa các lần demo |
| `top_p` | 0.2 | Cắt phần đuôi phân phối — nơi model bắt đầu bịa số liệu |

Provider không nhận `top_p` → tự bỏ tham số và gọi lại, không crash.

### 6.4 Chuẩn hoá metadata (không bịa dữ liệu)

- Tên nguồn: `title` → `source` → `file_name` → `filename` → `"Unknown source"`
- Năm: `year` → năm trong `date` → năm 19xx/20xx trong tên file/URL → `"n.d."`
- URL: chỉ chấp nhận `http`/`https`; `javascript:`/`data:` bị loại bỏ
- Thiếu score → hiển thị **"Không có điểm"**, không sinh số giả

### 6.5 Chống prompt injection

`sanitize_for_prompt()` loại ký tự điều khiển, vô hiệu hoá marker `[SOURCE n]`,
trung hoà nhãn `SYSTEM:` / `ASSISTANT:` trong nội dung tài liệu. Context được bọc
trong `<<<BEGIN_CONTEXT>>>` / `<<<END_CONTEXT>>>` và system prompt nói rõ nội dung
bên trong là **dữ liệu, không phải chỉ thị**.

### 6.6 Sentinel khi thiếu evidence

Retrieval trả rỗng → trả về **chính xác** `I cannot verify this information`
(không dịch, không thêm ký tự) và **không gọi LLM**.

---

## 7. Cách kiểm tra

### 7.1 Test Task 10

```bash
python -m pytest tests/test_individual.py -k "Task10" -v
```

### 7.2 Toàn bộ test suite

```bash
python -m pytest tests/ -v
```

### 7.3 Chạy module Task 10 độc lập

```bash
python -m src.task10_generation
```

### 7.4 Kiểm tra app import được

```bash
python -c "import app"
```

(Cảnh báo `missing ScriptRunContext` là bình thường khi import ngoài Streamlit.)

### 7.5 Kiểm tra citation

1. Đặt câu hỏi trong domain (ví dụ về học phí).
2. Trong câu trả lời, citation `[Nguồn, Năm]` được **highlight** (viền cyan).
3. Mở **Evidence panel** → đối chiếu tên nguồn trong citation với source card.
4. Nếu LLM bịa nguồn, UI hiện cảnh báo *"Có citation không khớp nguồn"* —
   `validate_citations()` so từng citation với `allowed_citations()` của các chunk thật.

---

## 8. Kết quả test thực tế

Môi trường: Windows 11, Python 3.11.0, Node v22.17.0, Streamlit 1.60.0.

### 8.1 Trước khi làm (baseline)

```
1 failed, 32 passed, 2 skipped
FAILED TestTask6::test_keyword_match_scores_higher — ModuleNotFoundError: rank_bm25
```

### 8.2 Sau khi làm

```
python -m pytest tests/ -v
============================= 35 passed in 3.05s ==============================
```

**35/35 passed** — đạt tiêu chí `CP4 Passed` trong `LAB_GUIDE.md`.

> Test Task 6 fail ở baseline là do **thiếu gói `rank-bm25`** trong môi trường máy,
> không phải lỗi code. Đã khắc phục bằng `pip install rank-bm25` (gói này đã có sẵn
> trong `requirements.txt`). **Không sửa một dòng code nào của Task 6.**

### 8.3 Build frontend

```
npm run build
✓ 2360 modules transformed.
dist/index.html                        0.48 kB │ gzip:   0.30 kB
dist/assets/index-LhuFZ1NC.css        20.50 kB │ gzip:   4.98 kB
dist/assets/KnowledgeOrb-DgM28Vo5.js   2.98 kB │ gzip:   1.31 kB
dist/assets/index-BFNmpjvy.js        565.66 kB │ gzip: 160.74 kB
dist/assets/three-Ba14jF7k.js        958.65 kB │ gzip: 265.06 kB
✓ built in 20.04s
```

`npm run build` chạy `tsc --noEmit` trước ⇒ **0 lỗi TypeScript** (strict mode).
Three.js nằm ở chunk riêng, chỉ tải khi scene 3D mount.

### 8.4 Kiểm thử thủ công trên trình duyệt

| Kiểm thử | Kết quả |
|----------|---------|
| `streamlit run app.py --server.headless true` | Khởi động sạch, không lỗi |
| React component mount | 1 iframe, WebGL canvas hoạt động, 0 lỗi console |
| Click câu hỏi gợi ý → trả lời | 470 ms · 5 nguồn · trace đầy đủ 8 bước |
| Chống xử lý trùng (nonce) | 1 lần click → đúng **1** message, không loop |
| Follow-up "Còn học bổng thì sao?" | Ghép ngữ cảnh từ lượt trước, retrieval chạy đúng |
| PageIndex fallback | cosine 0.436 < 0.48 → trace `fallback`, badge tím hiện |
| Query vô nghĩa | PageIndex trả 0 kết quả → trace ghi "Đã gọi nhưng không dùng kết quả" |
| Responsive 375px | 1 cột, **không** tràn ngang |
| Responsive 768px | 1–2 cột tuỳ bề rộng iframe, không tràn |
| Responsive 1600px | 3 cột `200px / 592px / 310px`, chat rộng nhất |
| Xoá `dist/` rồi reload | Tự chuyển native, 0 iframe, **không crash** |
| Đường sinh câu trả lời (provider giả lập) | citation hợp lệ 2/2, phát hiện citation bịa, xử lý `rate_limit` |
| API key trong output | Không xuất hiện ở bất kỳ đâu |

---

## 9. Cách demo từng tính năng

### 9.1 Conversation memory
1. Hỏi: *"Học phí tại RMIT Vietnam được thanh toán như thế nào?"*
2. Hỏi tiếp: *"Còn học bổng thì sao?"*
3. Bước **Câu hỏi** trong pipeline trace hiện ghi chú *"Đã ghép ngữ cảnh từ lượt hỏi trước"*.

Cơ chế: `resolve_follow_up()` **deterministic thuần** (nhận diện tiền tố "còn/vậy/thế…",
tham chiếu hồi chỉ, câu ngắn thiếu từ khoá domain) — không cần LLM nên vẫn chạy khi mất API.
Prompt chỉ nhận tối đa **4 lượt gần nhất**, đã lọc sạch source card/metadata.

### 9.2 Source inspector
Mở **Evidence panel**. Mỗi card hiển thị: rank · tên tài liệu · loại (legal/news) ·
retrieval type · **score kèm đúng tên metric** · năm · chunk ID · trích đoạn có
highlight từ khoá · nút Mở rộng / Chép / Mở nguồn.

> **Điểm đáng nói khi demo:** RRF score hiển thị dạng **raw** (`0.0164 · RRF fusion score`),
> **không** quy đổi phần trăm — vì RRF chỉ phụ thuộc thứ hạng, top-1 luôn ≈ 1/(60+1)
> bất kể nội dung có liên quan hay không. Chỉ cosine similarity mới được hiển thị %.

### 9.3 PageIndex fallback
Hỏi một câu mà semantic search cho cosine thấp (ví dụ *"Điều kiện để nhận học bổng
thành tích học tập là gì?"* → cosine 0.436 < 0.48). Evidence panel hiện banner tím
*"Pipeline đã chuyển sang PageIndex vectorless fallback"*, trace đổi bước PageIndex
sang trạng thái `fallback`.

Trạng thái này **luôn phản ánh dữ liệu thật**: nếu Task 9 không dùng PageIndex,
trace ghi `Bỏ qua` / `Đã gọi nhưng không dùng kết quả`, không bao giờ giả lập.

### 9.4 Không bịa thông tin
Hỏi câu ngoài domain. Khi có API key, LLM trả đúng `I cannot verify this information`.
Khi retrieval không có evidence, app trả sentinel này **mà không gọi LLM**.

---

## 10. Kịch bản live demo 3 phút

| Thời điểm | Nội dung |
|-----------|----------|
| 0:00 | Mở `streamlit run app.py`. Giới thiệu header: badge **ChromaDB · BM25 · RRF · PageIndex** phản ánh trạng thái thật. Chỉ vào Three.js KnowledgeOrb — 6 node = 6 chủ đề dịch vụ. |
| 0:20 | Giới thiệu **Hybrid Retrieval**: semantic (ChromaDB, cosine) chạy song song BM25, hợp nhất bằng RRF k=60. |
| 0:40 | Click gợi ý *"Học phí tại RMIT Vietnam được thanh toán như thế nào?"*. Chỉ typing indicator + xung sáng lan trên orb. |
| 1:00 | Mở **Evidence panel** — 5 source card thật, tên file, chunk ID, trích đoạn highlight từ khoá. |
| 1:20 | Chỉ **citation** `[student-fees-and-charges-guide-2026.md, 2026]` được highlight trong câu trả lời, đối chiếu với source card. Nói rõ tại sao RRF hiển thị raw score chứ không phải %. |
| 1:45 | Hỏi follow-up *"Còn học bổng thì sao?"* → chứng minh **conversation memory** qua ghi chú trong pipeline trace. |
| 2:10 | Mở **Pipeline trace** — thời gian THẬT từng chặng (semantic ~400ms, BM25 ~70ms, RRF, reorder, generation, citation validation). |
| 2:30 | Hỏi câu ngoài domain → hệ thống **không bịa**, trả `I cannot verify this information`; hoặc chỉ PageIndex fallback khi cosine < 0.48. |
| 2:50 | Kết: sơ đồ kiến trúc mục 3 — Streamlit giữ logic, React chỉ trình bày, và **luôn có fallback native** nên demo không bao giờ chết. |

---

## 11. Bảo mật & tính trung thực dữ liệu

- Không hardcode secret; `.env` đã nằm trong `.gitignore`.
- Không log API key / authorization header. `provider_status()` chỉ trả tên provider + model.
- **Không render HTML từ LLM.** Native: citation được bọc thành inline code (markdown,
  không HTML). React: `react-markdown` **không bật** `rehype-raw`. `unsafe_allow_html`
  chỉ dùng cho chuỗi HTML tĩnh do chính app tạo, mọi giá trị động đều qua `escape_attr()`.
- Link nguồn chỉ mở `http`/`https`, kèm `rel="noopener noreferrer"`.
- Nội dung tài liệu không bao giờ được coi là system instruction (mục 6.5).
- **Không có dữ liệu giả:** source, score, citation, pipeline status đều từ lần chạy thật.

---

## 12. Accessibility & Performance

**Accessibility:** contrast theo design token; `:focus-visible` rõ ràng; mọi nút có
`aria-label`; trạng thái luôn có **icon + chữ**, không chỉ dựa vào màu; typing indicator
dùng `role="status"` + `aria-live`; evidence panel có `aria-expanded`/`aria-controls`;
tôn trọng `prefers-reduced-motion` **và** toggle "Giảm chuyển động" trong app.

**Performance:** chỉ animate `transform`/`opacity`; three.js ở chunk riêng, lazy-load
sau 120ms; `dpr` giới hạn `[1, 1.75]` (1.2 trên máy yếu); tắt antialias khi
`hardwareConcurrency <= 4` hoặc màn hình < 768px; `frameloop="demand"` khi reduced-motion;
không shadow, không post-processing; canvas `pointer-events: none`; excerpt gửi sang
React cắt còn 600 ký tự; history gửi component giới hạn 40 message.

---

## 13. Giới hạn còn lại & phụ thuộc thành viên khác

### 13.1 Cần API key để demo trọn vẹn (Role 1)
Máy hiện tại **chưa có `.env`**, nên đường gọi LLM thật chưa chạy được end-to-end.
Đường sinh câu trả lời đã được kiểm chứng bằng **provider giả lập** (citation hợp lệ,
phát hiện citation bịa, xử lý `rate_limit` / `timeout` / `auth`). Chỉ cần thêm
`OPENROUTER_API_KEY` vào `.env` là chạy thật ngay, không phải sửa code.

### 13.2 ChromaDB chưa được index (Role 2)
`chroma_db/` hiện chỉ có `fallback_index.json`, **chưa có vector store thật**, và máy
chưa cài `chromadb` + `sentence-transformers`. Hệ quả:

- `semantic_search()` (Task 5) rơi vào nhánh dự phòng in-memory dùng **hashing embedding**
  thay cho `BAAI/bge-m3` ⇒ điểm cosine thấp hơn thực tế (0.2–0.5 thay vì 0.6–0.8).
- Vì threshold là 0.48, **PageIndex fallback bị kích hoạt nhiều hơn bình thường**.

Đây là phụ thuộc vào Role 2, **không phải lỗi Role 4** — Role 4 cố ý không cài
`chromadb` vì cài mà không index sẽ khiến `semantic_search()` trả về rỗng
(collection trống), tức là *tệ hơn* hiện trạng.

**Cách khắc phục (Role 2 chạy):**

```bash
pip install chromadb sentence-transformers langchain-text-splitters
python -m src.task4_chunking_indexing
```

Sau đó badge **ChromaDB** trên header tự chuyển xanh kèm số vectors — không cần sửa
gì ở `app.py`.

### 13.3 PageIndex chạy chế độ local (Role 3)
Chưa có `PAGEINDEX_API_KEY` nên `pageindex_search()` dùng nhánh vectorless local
(xếp hạng section theo term overlap). Giao diện đã sẵn sàng cho cả hai chế độ và
hiển thị đúng nhãn `PageIndex term overlap`.

### 13.4 Ghi chú kỹ thuật khác
- `_instrumented_retrieve()` tạm bọc các tham chiếu hàm trong namespace của
  `task9_retrieval_pipeline` để đo thời gian, và **luôn khôi phục trong `finally`**.
  Có `threading.Lock` để tránh tranh chấp giữa nhiều session Streamlit.
- Bundle `three-*.js` ~959 kB (265 kB gzip). Chấp nhận được vì tải lazy và bundle
  offline hoàn toàn (yêu cầu bài: **không dùng CDN**).
- `dist/` được commit để người khác clone về chạy ngay không cần cài Node.
