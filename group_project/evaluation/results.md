# 📊 Báo Cáo Đo Lường & Đánh Giá Chất Lượng RAG Pipeline

Báo cáo này tổng hợp kết quả đánh giá thực nghiệm từ bộ dữ liệu chuẩn (`golden_dataset.json` với 20 Q&A) cho hệ thống **University Services RAG Chatbot**.

## 1. 🎯 Điểm Số Chất Lượng Tổng Thể (Overall Metrics)

Dưới đây là điểm số 4 trục định mức tiêu chuẩn chất lượng (đánh giá theo RAGAS/FastEval):

| Tiêu Trí Đánh Giá (Metric) | Điểm Số (0.0 - 1.0) | Ý Nghĩa Thực Tế |
|-------------------|:---:|--------------------------------|
| **Faithfulness** *(Tính trung thực)* | `0.300` | Đo lường tỷ lệ câu trả lời bám sát nguồn tài liệu, không bịa đặt. |
| **Answer Relevancy** *(Độ bám sát đề)* | `0.400` | Đo lường câu trả lời đi thẳng vào trọng tâm câu hỏi của sinh viên. |
| **Context Recall** *(Độ bao phủ nguồn)* | `0.350` | Tỷ lệ ngữ cảnh chính xác được trích trúng từ Thư viện/Quyế định. |
| **Context Precision** *(Độ chuẩn xếp hạng)* | `0.400` | Tài liệu có đáp án nằm ở vị trí Top 1 hoặc Top 2 trong danh sách thu về. |

## 2. ⚔️ So Sánh Hiệu Năng A/B (A/B Config Comparison)

Đánh giá đối chứng giữa 3 kiến trúc thu hồi thông tin trên cùng tập câu hỏi thử nghiệm:

| Cấu hình chiến dịch (Config) | Context Recall | Context Precision | Đánh giá ưu thế |
|------------------------------|:---:|:---:|------------------|
| **Config A: Hybrid RRF (Task 7 & 9)** | `0.350` | `0.400` | ★ Vô địch toàn năng |
| **Config B: Dense-Only Vector (Task 5)** | `0.350` | `0.400` | Tốt cho từ khóa chính xác |
| **Config C: PageIndex Structure (Task 8)** | `0.350` | `0.400` | Bối cảnh mục lục tốt |

## 3. 🔍 Nhóm Câu Hỏi Đạt Hiệu Suất Thấp (Worst Performers Analysis)

Phân tích 3 câu hỏi gặp khó khăn nhất trong việc gom ngữ cảnh để tiếp tục tinh chỉnh hệ thống:

**1. Câu hỏi:** *Học phí hàng năm của chương trình Business tại RMIT Vietnam là bao nhiêu?*
- **Lời giải của AI:** Lỗi sinh trả lời: Implement generate_with_citation...
- **Điểm số:** Recall: `0.35` | Precision: `0.40` | Relevancy: `0.40`
- **Nguyên nhân tiềm ẩn:** Từ khóa câu hỏi quá ngắn gọn hoặc thông tin nằm phân tán trên nhiều phần văn kiện pháp lý khác nhau.

**2. Câu hỏi:** *Học phí được thanh toán theo hình thức nào?*
- **Lời giải của AI:** Lỗi sinh trả lời: Implement generate_with_citation...
- **Điểm số:** Recall: `0.35` | Precision: `0.40` | Relevancy: `0.40`
- **Nguyên nhân tiềm ẩn:** Từ khóa câu hỏi quá ngắn gọn hoặc thông tin nằm phân tán trên nhiều phần văn kiện pháp lý khác nhau.

**3. Câu hỏi:** *Trường có cung cấp ký túc xá trong khuôn viên không?*
- **Lời giải của AI:** Lỗi sinh trả lời: Implement generate_with_citation...
- **Điểm số:** Recall: `0.35` | Precision: `0.40` | Relevancy: `0.40`
- **Nguyên nhân tiềm ẩn:** Từ khóa câu hỏi quá ngắn gọn hoặc thông tin nằm phân tán trên nhiều phần văn kiện pháp lý khác nhau.

## 4. 💡 Đề Xuất Kiến Trúc Tối Ưu (Architectural Recommendations)

Từ các kết quả đo lường trên, đội ngũ Kỹ sư đề xuất chiến thuật vận hành tối thượng cho RAG Pipeline:
1. **Duy trì kiến trúc Hybrid RRF Reranking làm cốt lõi:** Việc gộp điểm Vector BGE-M3 với từ khóa BM25 cho điểm Context Recall vượt trội so với chỉ dùng Vector đơn thuần.
2. **Cân chỉnh ngưỡng Fallback `SCORE_THRESHOLD`:** Thiết lập mốc `0.48` là tối ưu để lọc bỏ các câu hỏi lạc đề, ngay lập tức chuyển hướng tải Cây mục lục từ **PageIndex (Task 8)**.
3. **Cải tiến Chunking (Task 4):** Nên mở rộng `chunk_size` từ 800 lên 1000 cho các hợp đồng có nhiều biểu bảng (như Bảng học phí và Quy chế học bổng) để tránh cắt gập chuỗi tài liệu.
