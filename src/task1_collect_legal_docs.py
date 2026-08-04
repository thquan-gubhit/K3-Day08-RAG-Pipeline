"""
Task 1 — Thu thập văn bản chính sách/quy định dịch vụ đại học.

Hướng dẫn:
    1. Tìm tối thiểu 3 văn bản chính sách (PDF/DOCX) từ trang công khai của một trường đại học.
    2. Tải về và lưu vào data/landing/legal/
    3. Đặt tên file rõ ràng, không dấu, mô tả đúng nội dung.

Gợi ý nguồn (ví dụ trang công khai RMIT Vietnam — rmit.edu.vn):
    - https://www.rmit.edu.vn/study-at-rmit/tuition-fees
    - https://www.rmit.edu.vn/study-at-rmit/scholarships/...
    - https://www.rmit.edu.vn/students/my-studies/fees-and-payments

Gợi ý văn bản (chủ đề dịch vụ đại học):
    - Học phí & phương thức thanh toán (Tuition Fees)
    - Chính sách học bổng (Scholarship eligibility)
    - Quy định ký túc xá / hỗ trợ chỗ ở (Accommodation Services)
    - Hướng dẫn đăng ký học phần qua cổng thông tin sinh viên (Course Registration)

Lưu ý: một số trang trường (vd VinUni, Fulbright) chặn bot crawler mặc định (HTTP 403) —
không phải lỗi của bạn, đó là cấu hình WAF/Cloudflare phía server. Đổi sang trang khác
thay vì cố vượt qua, và chỉ dùng nguồn công khai/được phép chia sẻ.
"""

from pathlib import Path

import requests

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"


LEGAL_DOCUMENTS = [
    {
        "url": "https://www.rmit.edu.vn/content/dam/rmit/vn/en/assets-for-production/documents/pdfs/vn-parents-guide/en-parents-guide-2026.pdf",
        "filename": "parents-family-guide-2026.pdf",
    },
    {
        "url": "https://www.rmit.edu.vn/content/dam/rmit/vn/en/assets-for-production/documents/pdfs/study-at-rmit/programs/english-pdf/doctor-of-philosophy/scholarships-for-phd-students/rmit-university-vietnam-scholarship-terms-and-conditions.pdf",
        "filename": "scholarship-terms-and-conditions.pdf",
    },
    {
        "url": "https://www.rmit.edu.vn/assets/vn/en/assets-for-production/documents/pdfs/study-at-rmit/tuition-fees/student-fees-and-charges-guide-06-2026.pdf",
        "filename": "student-fees-and-charges-guide-2026.pdf",
    },
]


def setup_directory():
    """Tạo thư mục data/landing/legal/ nếu chưa có."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"✓ Thư mục đã sẵn sàng: {DATA_DIR}")


def download_file(url: str, filename: str, overwrite: bool = False) -> Path:
    """Download one public PDF and reject HTML/error responses."""
    setup_directory()
    filepath = DATA_DIR / filename
    if filepath.exists() and filepath.stat().st_size > 1024 and not overwrite:
        print(f"- Đã có: {filepath.name}")
        return filepath

    response = requests.get(url, timeout=90, stream=True)
    response.raise_for_status()
    content = response.content
    if not content.startswith(b"%PDF-"):
        raise ValueError(f"Nguồn không trả về PDF hợp lệ: {url}")
    filepath.write_bytes(content)
    print(f"✓ Đã tải: {filepath.name} ({len(content):,} bytes)")
    return filepath


def collect_legal_documents(overwrite: bool = False) -> list[Path]:
    """Collect and validate all configured legal/policy documents."""
    files = [
        download_file(item["url"], item["filename"], overwrite=overwrite)
        for item in LEGAL_DOCUMENTS
    ]
    if len(files) < 3:
        raise RuntimeError("Task 1 yêu cầu tối thiểu 3 tài liệu")
    return files


if __name__ == "__main__":
    print("=" * 50)
    print("Task 1: Collect legal/policy PDF documents")
    print("=" * 50)
    collected = collect_legal_documents()
    print(f"\n✓ Hoàn thành: {len(collected)} tài liệu trong {DATA_DIR}")
