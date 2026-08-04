"""
Task 8 — PageIndex Vectorless RAG.

Đăng ký tài khoản tại: https://pageindex.ai/
SDK & sample code: https://github.com/VectifyAI/PageIndex

PageIndex cho phép RAG mà không cần vector store — sử dụng
structural understanding của document thay vì embedding.

Cài đặt:
    pip install pageindex

Hướng dẫn:
    1. Đăng ký account tại pageindex.ai
    2. Lấy API key
    3. Upload documents
    4. Query sử dụng PageIndex API

Lưu ý: API `/retrieval` của PageIndex hiện đã deprecated (vẫn hoạt động, nhưng response
có field "deprecation" cảnh báo) và trả kết quả trong "retrieved_nodes" — mỗi node có
"relevant_contents": list[list[{section_title, relevant_content}]]. In response thật ra
(json.dumps(...)) trước khi viết logic parse, đừng đoán schema từ ví dụ code cũ.
"""

import os
import json
import time
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "")
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
DOC_IDS_FILE = Path(__file__).parent.parent / "data" / "pageindex_doc_ids.json"
LEGAL_LANDING_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"



def get_pageindex_client():
    if not PAGEINDEX_API_KEY:
        return None
    try:
        from pageindex.client import PageIndexClient
        return PageIndexClient(api_key=PAGEINDEX_API_KEY)
    except ImportError:
        try:
            from pageindex import PageIndexClient
            return PageIndexClient(api_key=PAGEINDEX_API_KEY)
        except Exception:
            print("⚠ Chưa cài thư viện pageindex. Vui lòng chạy: pip install pageindex")
            return None


def upload_documents():
    """
    Upload tài liệu lên PageIndex và lưu lại danh sách doc_id vào file JSON.
    Ưu tiên upload các file PDF gốc trong data/landing/legal, nếu là .md thì convert tạm sang PDF bằng fpdf2.
    """
    client = get_pageindex_client()
    if not client:
        print("⚠ Không thể khởi tạo PageIndexClient (thiếu PAGEINDEX_API_KEY hoặc chưa cài pip install pageindex).")
        return {}

    doc_mapping = {}
    if DOC_IDS_FILE.exists():
        try:
            doc_mapping = json.loads(DOC_IDS_FILE.read_text(encoding="utf-8"))
        except Exception:
            doc_mapping = {}

    print("\n[Task 8] Đang kiểm tra và upload tài liệu lên PageIndex Cloud...")

    # 1. Upload các file PDF chuẩn từ Thư viện pháp lý (legal)
    if LEGAL_LANDING_DIR.exists():
        for pdf_file in sorted(LEGAL_LANDING_DIR.glob("*.pdf")):
            if pdf_file.name in doc_mapping:
                print(f"  ✓ Đã có sẵn trên Cloud: {pdf_file.name} (ID: {doc_mapping[pdf_file.name]})")
                continue
            print(f"  → Đang upload PDF gốc lên PageIndex: {pdf_file.name} ...")
            try:
                resp = client.submit_document(str(pdf_file))
                doc_id = resp.get("doc_id") or resp.get("id")
                if doc_id:
                    doc_mapping[pdf_file.name] = doc_id
                    print(f"    ✓ Thành công -> doc_id: {doc_id}")
            except Exception as e:
                print(f"    ❌ Lỗi upload {pdf_file.name}: {e}")

    # 2. Với các bài báo Markdown trong news/, convert nhanh sang PDF bằng fpdf2 rồi upload
    temp_dir = Path(__file__).parent.parent / "data" / "temp_pdf"
    temp_dir.mkdir(parents=True, exist_ok=True)

    for md_file in sorted(STANDARDIZED_DIR.rglob("*.md")):
        if md_file.name in doc_mapping:
            continue
        try:
            from fpdf import FPDF
            pdf_path = temp_dir / f"{md_file.stem}.pdf"
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", size=11)
            text = md_file.read_text(encoding="utf-8", errors="ignore")
            # FPDF cơ sở chỉ hỗ trợ ký tự Latin/ASCII cơ bản, chuyển hóa thuần túy
            clean_text = text.encode("latin-1", "replace").decode("latin-1")
            for line in clean_text.split("\n"):
                pdf.multi_cell(0, 6, txt=line)
            pdf.output(str(pdf_path))

            print(f"  → Đang upload file chuyển đổi từ Markdown: {md_file.name} ...")
            resp = client.submit_document(str(pdf_path))
            doc_id = resp.get("doc_id") or resp.get("id")
            if doc_id:
                doc_mapping[md_file.name] = doc_id
                print(f"    ✓ Thành công -> doc_id: {doc_id}")
        except Exception as e:
            print(f"    ⚠ Bỏ qua upload {md_file.name}: {e}")

    DOC_IDS_FILE.write_text(json.dumps(doc_mapping, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n✔ Trạng thái lưu trữ Document IDs của PageIndex được ghi tại: {DOC_IDS_FILE.name}")
    return doc_mapping


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """
    Vectorless retrieval sử dụng PageIndex Cloud API.
    Dùng làm fallback khi hybrid search không có kết quả tốt.
    """
    if not query.strip() or top_k <= 0:
        return []

    # Nếu có API Key, thực hiện tra cứu theo cây mục lục PageIndex Cloud thực sự
    if PAGEINDEX_API_KEY:
        client = get_pageindex_client()
        if client and DOC_IDS_FILE.exists():
            try:
                doc_mapping = json.loads(DOC_IDS_FILE.read_text(encoding="utf-8"))
                results = []
                rank_idx = 0
                for doc_name, doc_id in list(doc_mapping.items())[:2]:  # Truy vấn tối đa 2 doc tài liệu chuẩn
                    try:
                        resp = client.submit_query(doc_id=doc_id, query=query)
                        retrieval_id = resp.get("retrieval_id") or resp.get("id")
                        if not retrieval_id:
                            continue

                        # Poll cho đến khi status hoàn thành (tối đa 10s)
                        for _ in range(5):
                            time.sleep(1.5)
                            retrieval = client.get_retrieval(retrieval_id)
                            if retrieval.get("status") in ["completed", "success", "done", "finished"]:
                                break

                        for node in retrieval.get("retrieved_nodes", [])[:2]:
                            for group in node.get("relevant_contents", []):
                                for item in group:
                                    score = max(0.4, 0.85 - (rank_idx * 0.05))
                                    results.append({
                                        "content": item.get("relevant_content", "") or item.get("content", ""),
                                        "score": float(score),
                                        "metadata": {"section": item.get("section_title", doc_name), "source": doc_name},
                                        "source": "pageindex",
                                    })
                                    rank_idx += 1
                    except Exception as e:
                        print(f"⚠ Lỗi tra cứu PageIndex trên tài liệu {doc_name}: {e}")

                if results:
                    return sorted(results, key=lambda x: x["score"], reverse=True)[:top_k]
            except Exception as e:
                print(f"⚠ Không thể hoàn tất truy vấn qua API ({e}). Đang dùng fallback nội bộ.")

    # Fallback nội bộ phi vector: So khớp theo section heading của Markdown
    # Lưu giữ hoàn toàn cấu trúc văn kiện mà không băm nhỏ thành chunk.
    import re
    query_terms = set(re.findall(r"\w+", query.lower(), flags=re.UNICODE))
    candidates = []
    for md_file in sorted(STANDARDIZED_DIR.rglob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        sections = re.split(r"(?=^#{1,3}\s+)", text, flags=re.MULTILINE)
        for section in sections:
            if not section.strip():
                continue
            terms = set(re.findall(r"\w+", section.lower(), flags=re.UNICODE))
            overlap = len(query_terms & terms)
            if overlap:
                candidates.append({
                    "content": section.strip(),
                    "score": overlap / max(1, len(query_terms)),
                    "metadata": {"source": md_file.name, "type": "pageindex_section"},
                    "source": "pageindex",
                })
    return sorted(candidates, key=lambda item: item["score"], reverse=True)[:top_k]


if __name__ == "__main__":
    if not PAGEINDEX_API_KEY:
        print("⚠ Hãy set PAGEINDEX_API_KEY trong file .env")
        print("  Đăng ký tại: https://pageindex.ai/")
    else:
        print("Uploading documents...")
        upload_documents()

        print("\nTest query:")
        results = pageindex_search("tuition fee payment methods", top_k=3)
        for r in results:
            print(f"[{r['score']:.3f}] {r['content'][:100]}...")
