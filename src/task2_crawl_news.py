"""
Task 2 — Crawl bài viết/thông báo về dịch vụ đại học.

Hướng dẫn:
    1. Crawl tối thiểu 5 bài viết từ trang công khai của một trường đại học.
    2. Sử dụng Crawl4AI hoặc thư viện crawling tương tự.
    3. Lưu output vào data/landing/news/
    4. Mỗi bài lưu 1 file JSON với metadata (url, title, date_crawled, content).

Cài đặt:
    pip install crawl4ai
    playwright install chromium   # bắt buộc — pip install crawl4ai KHÔNG tự tải browser binary,
                                   # thiếu bước này sẽ báo lỗi
                                   # "BrowserType.launch: Executable doesn't exist"

Gợi ý chủ đề: thông báo tuyển sinh, sự kiện, dịch vụ thư viện, hỗ trợ sinh viên, học bổng.
"""

import asyncio
import json
import re
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"


def setup_directory():
    """Tạo thư mục data/landing/news/ nếu chưa có."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)


# Nguồn công khai chính thức của RMIT Vietnam.
ARTICLE_URLS = [
    "https://www.rmit.edu.vn/study-at-rmit/tuition-fees",
    "https://www.rmit.edu.vn/students/my-studies/fees-and-payments/tuition-fees-faq-and-support",
    "https://www.rmit.edu.vn/study-at-rmit/scholarships/current-student-scholarships",
    "https://www.rmit.edu.vn/study-at-rmit/tuition-fees/payment-methods",
    "https://www.rmit.edu.vn/about-us/rmit-parents-and-family/family-connect/fees-and-payment",
]


class _ReadableHTML(HTMLParser):
    """Small dependency-free HTML-to-readable-text extractor."""
    def __init__(self):
        super().__init__()
        self.title, self.parts, self._in_title, self._ignored = "", [], False, 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript", "svg"}:
            self._ignored += 1
        elif tag == "title":
            self._in_title = True
        elif tag in {"h1", "h2", "h3", "p", "li", "br"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript", "svg"} and self._ignored:
            self._ignored -= 1
        elif tag == "title":
            self._in_title = False

    def handle_data(self, data):
        if self._ignored:
            return
        text = unescape(data).strip()
        if self._in_title and text:
            self.title += text
        elif text:
            self.parts.append(text)


async def crawl_article(url: str) -> dict:
    """
    Crawl một bài viết và trả về dict chứa metadata + content.

    Returns:
        {
            "url": str,
            "title": str,
            "date_crawled": str (ISO format),
            "content_markdown": str
        }
    """
    import requests

    def fetch():
        response = requests.get(url, timeout=90, headers={"User-Agent": "Day8-RAG-Lab/1.0"})
        response.raise_for_status()
        parser = _ReadableHTML()
        parser.feed(response.text)
        content = "\n\n".join(
            line.strip() for line in re.split(r"\n+", " ".join(parser.parts)) if line.strip()
        )
        if len(content) < 500:
            raise ValueError(f"Nội dung crawl quá ngắn: {url}")
        return {
            "url": url,
            "title": parser.title or "RMIT Vietnam article",
            "date_crawled": datetime.now().isoformat(),
            "content_markdown": content,
        }

    return await asyncio.to_thread(fetch)


async def crawl_all():
    """Crawl toàn bộ bài viết trong ARTICLE_URLS."""
    setup_directory()

    for i, url in enumerate(ARTICLE_URLS, 1):
        print(f"[{i}/{len(ARTICLE_URLS)}] Crawling: {url}")
        article = await crawl_article(url)

        # Lưu file JSON
        filename = f"article_{i:02d}.json"
        filepath = DATA_DIR / filename
        filepath.write_text(json.dumps(article, ensure_ascii=False, indent=2))
        print(f"  ✓ Saved: {filepath}")


if __name__ == "__main__":
    if not ARTICLE_URLS:
        print("⚠ Hãy điền ARTICLE_URLS trước khi chạy!")
        print("Gợi ý: tìm trang thông báo/sự kiện trên trang chính thức của trường đại học")
    else:
        asyncio.run(crawl_all())
