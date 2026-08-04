"""
Role 4 — Tầng dịch vụ ghép Retrieval (Task 9) và Generation (Task 10) cho chatbot.

Module này là ADAPTER, không phải bản viết lại của Task 1–9:
    - Không sửa file của thành viên khác.
    - Không đổi output của ``retrieve()`` hay ``generate_with_citation()``.
    - Thu thập pipeline trace bằng cách tạm bọc (wrap) các tham chiếu hàm trong
      namespace của ``task9_retrieval_pipeline`` để đo thời gian và số document
      THẬT ở từng chặng, rồi khôi phục nguyên trạng trong ``finally``.

Toàn bộ số liệu hiển thị trên UI đều lấy từ lần chạy thật. Không có bước nào
được giả lập: nếu PageIndex không được gọi, trace ghi trạng thái "skipped".
"""

from __future__ import annotations

import json
import re
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from . import task9_retrieval_pipeline as t9
from .task10_generation import (
    CANNOT_VERIFY,
    MAX_HISTORY_TURNS,
    generate_with_citation,
    normalize_source,
    provider_status,
    validate_citations,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHROMA_DIR = PROJECT_ROOT / "chroma_db"
STANDARDIZED_DIR = PROJECT_ROOT / "data" / "standardized"
FRONTEND_DIST = PROJECT_ROOT / "components" / "university_chat_ui" / "frontend" / "dist"

# Patch module-global nên phải serialise giữa các session Streamlit.
_TRACE_LOCK = threading.Lock()

MAX_QUERY_CHARS = 500


# =============================================================================
# PIPELINE TRACE
# =============================================================================

# Thứ tự các bước hiển thị trên UI. Mỗi bước bắt đầu ở trạng thái "idle" và chỉ
# đổi trạng thái khi thực sự chạy.
STEP_ORDER = [
    ("query", "Câu hỏi"),
    ("semantic", "Semantic Search (ChromaDB)"),
    ("lexical", "BM25 Lexical Search"),
    ("fusion", "RRF Fusion / Reranking"),
    ("pageindex", "PageIndex Vectorless Fallback"),
    ("reorder", "Document Reordering"),
    ("generation", "LLM Generation"),
    ("citation", "Citation Validation"),
]


def _new_trace() -> list[dict]:
    """Khởi tạo trace với tất cả các bước ở trạng thái idle."""
    return [
        {"id": key, "label": label, "status": "idle", "ms": None, "count": None, "note": ""}
        for key, label in STEP_ORDER
    ]


def _set_step(
    trace: list[dict],
    step_id: str,
    *,
    status: Optional[str] = None,
    ms: Optional[float] = None,
    count: Optional[int] = None,
    note: Optional[str] = None,
) -> None:
    """Cập nhật một bước trong trace tại chỗ."""
    for step in trace:
        if step["id"] == step_id:
            if status is not None:
                step["status"] = status
            if ms is not None:
                step["ms"] = int(ms)
            if count is not None:
                step["count"] = count
            if note is not None:
                step["note"] = note
            return


def _instrumented_retrieve(query: str, top_k: int, trace: list[dict]) -> list[dict]:
    """
    Gọi ``task9.retrieve()`` trong lúc đo từng chặng con.

    Các hàm ``semantic_search`` / ``lexical_search`` / ``rerank_rrf`` / ``rerank``
    / ``pageindex_search`` được tạm thay bằng wrapper ghi lại thời gian và số
    kết quả, sau đó trả về nguyên giá trị gốc — logic Task 9 không đổi.
    """
    originals = {
        name: getattr(t9, name)
        for name in ("semantic_search", "lexical_search", "rerank_rrf", "rerank", "pageindex_search")
    }
    # Dùng list 1 phần tử để closure ghi được điểm cosine gốc.
    best_cosine: list[Optional[float]] = [None]

    def timed(step_id: str, fn: Callable[..., Any], on_result: Optional[Callable[[Any], None]] = None):
        def wrapper(*args, **kwargs):
            _set_step(trace, step_id, status="running")
            start = time.perf_counter()
            try:
                result = fn(*args, **kwargs)
            except Exception as exc:
                _set_step(
                    trace,
                    step_id,
                    status="error",
                    ms=(time.perf_counter() - start) * 1000,
                    note=type(exc).__name__,
                )
                raise
            elapsed = (time.perf_counter() - start) * 1000
            count = len(result) if isinstance(result, list) else None
            _set_step(trace, step_id, status="success", ms=elapsed, count=count)
            if on_result is not None:
                on_result(result)
            return result

        return wrapper

    def capture_cosine(result: Any) -> None:
        if isinstance(result, list) and result and isinstance(result[0], dict):
            score = result[0].get("score")
            if isinstance(score, (int, float)):
                best_cosine[0] = float(score)
                _set_step(
                    trace,
                    "semantic",
                    note=f"cosine tốt nhất {float(score):.3f}",
                )

    with _TRACE_LOCK:
        try:
            t9.semantic_search = timed("semantic", originals["semantic_search"], capture_cosine)
            t9.lexical_search = timed("lexical", originals["lexical_search"])
            t9.rerank_rrf = timed("fusion", originals["rerank_rrf"])
            # rerank() chạy sau rrf trong cùng bước hợp nhất — cộng dồn thời gian.
            t9.rerank = _accumulate("fusion", originals["rerank"], trace)
            t9.pageindex_search = timed("pageindex", originals["pageindex_search"])

            _set_step(trace, "query", status="success", count=1)
            results = t9.retrieve(query, top_k=top_k)
        finally:
            for name, fn in originals.items():
                setattr(t9, name, fn)

    threshold = getattr(t9, "SCORE_THRESHOLD", None)
    if best_cosine[0] is not None and isinstance(threshold, (int, float)):
        _set_step(
            trace,
            "semantic",
            note=f"cosine tốt nhất {best_cosine[0]:.3f} / ngưỡng {threshold:.2f}",
        )

    used_pageindex = bool(results) and str(results[0].get("source", "")).lower() == "pageindex"
    pageindex_step = next(s for s in trace if s["id"] == "pageindex")
    if used_pageindex:
        _set_step(trace, "pageindex", status="fallback", note="Đã dùng làm nguồn trả về")
    elif pageindex_step["status"] == "success":
        # Được gọi nhưng kết quả không được dùng (hybrid vẫn thắng).
        _set_step(trace, "pageindex", status="success", note="Đã gọi nhưng không dùng kết quả")
    elif pageindex_step["status"] == "idle":
        _set_step(trace, "pageindex", status="skipped", note="Không cần fallback")

    return results


def _accumulate(step_id: str, fn: Callable[..., Any], trace: list[dict]):
    """Wrapper cộng dồn thời gian vào một bước đã có (dùng cho rerank sau RRF)."""

    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = fn(*args, **kwargs)
        elapsed = (time.perf_counter() - start) * 1000
        for step in trace:
            if step["id"] == step_id:
                step["ms"] = int((step["ms"] or 0) + elapsed)
                if isinstance(result, list):
                    step["count"] = len(result)
                step["status"] = "success"
                break
        return result

    return wrapper


# =============================================================================
# CONVERSATION MEMORY
# =============================================================================

# Mở đầu câu báo hiệu chắc chắn là follow-up ("Còn học bổng thì sao?"). Các
# marker này được ưu tiên hơn cả từ khoá domain, vì câu vẫn thiếu ngữ cảnh dù
# có nhắc tên chủ đề mới.
_FOLLOW_UP_PREFIXES = (
    "còn", "thế còn", "vậy còn", "thế thì", "vậy thì", "vậy", "thế",
    "what about", "how about", "and", "and then", "so",
)

# Dấu hiệu tham chiếu hồi chỉ xuất hiện ở bất kỳ đâu trong câu.
_FOLLOW_UP_MARKERS = (
    "cái đó", "điều đó", "cái này", "việc đó", "như vậy", "trường hợp đó",
    "ở trên", "vừa rồi", "nói trên", "chi tiết hơn", "cụ thể hơn",
    "giải thích thêm", "nói rõ hơn", "that one", "the above",
)

# Từ khoá domain — câu đã có từ khoá riêng thì không cần ghép ngữ cảnh.
_DOMAIN_KEYWORDS = (
    "học phí", "học bổng", "ký túc xá", "kí túc xá", "đăng ký học phần", "thư viện",
    "hỗ trợ sinh viên", "chỗ ở", "thanh toán", "tuition", "scholarship",
    "accommodation", "library", "enrolment", "enrollment", "course registration",
)


def is_follow_up(query: str, history: list[dict]) -> bool:
    """
    Đoán xem câu hỏi có phải follow-up cần ngữ cảnh hay không — thuần deterministic,
    không gọi LLM (nên luôn hoạt động kể cả khi mất API).
    """
    if not history:
        return False
    lowered = query.lower().strip()

    # 1. Mở đầu bằng liên từ nối tiếp → chắc chắn là follow-up.
    if any(re.match(rf"^{re.escape(prefix)}\b", lowered) for prefix in _FOLLOW_UP_PREFIXES):
        return True

    # 2. Có tham chiếu hồi chỉ ("cái đó", "ở trên"...) → follow-up.
    if any(marker in lowered for marker in _FOLLOW_UP_MARKERS):
        return True

    # 3. Đã tự chứa từ khoá domain → đủ ngữ cảnh, không cần ghép.
    if any(keyword in lowered for keyword in _DOMAIN_KEYWORDS):
        return False

    # 4. Câu rất ngắn, không có từ khoá domain → nhiều khả năng là follow-up.
    return len(lowered.split()) <= 6


def resolve_follow_up(query: str, history: list[dict]) -> str:
    """
    Ghép câu hỏi follow-up với chủ đề của lượt hỏi gần nhất để retrieval có đủ
    từ khoá. Trả về query gốc nếu không phải follow-up.

    Deterministic hoàn toàn: chỉ nối chuỗi, không nhờ LLM viết lại.
    """
    if not is_follow_up(query, history):
        return query
    previous = [m for m in history if m.get("role") == "user" and m.get("content")]
    if not previous:
        return query
    last_question = str(previous[-1]["content"]).strip()
    return f"{last_question} {query}".strip()


def history_for_prompt(messages: list[dict]) -> list[dict]:
    """
    Rút gọn lịch sử chat thành {'role','content'} cho prompt.

    Bỏ mọi source card / metadata / thông báo lỗi. Chỉ lấy tối đa
    ``MAX_HISTORY_TURNS`` lượt gần nhất (giới hạn thật nằm ở Task 10).
    """
    cleaned: list[dict] = []
    for message in messages:
        role = message.get("role")
        content = str(message.get("content") or "").strip()
        if role not in ("user", "assistant") or not content:
            continue
        if message.get("error"):
            continue
        cleaned.append({"role": role, "content": content})
    return cleaned[-(MAX_HISTORY_TURNS * 2):]


# =============================================================================
# VALIDATION
# =============================================================================

def validate_query(raw: str) -> tuple[bool, str, str]:
    """
    Kiểm tra câu hỏi trước khi chạy pipeline.

    Returns:
        (hợp lệ, query đã chuẩn hoá, thông báo lỗi tiếng Việt)
    """
    query = re.sub(r"\s+", " ", str(raw or "")).strip()
    if not query:
        return False, "", "Vui lòng nhập câu hỏi trước khi gửi."
    if len(query) < 3:
        return False, query, "Câu hỏi quá ngắn — hãy mô tả rõ hơn điều bạn muốn tra cứu."
    if len(query) > MAX_QUERY_CHARS:
        return False, query, f"Câu hỏi vượt quá {MAX_QUERY_CHARS} ký tự. Hãy rút gọn lại."
    return True, query, ""


# =============================================================================
# MAIN ENTRY — retrieve + generate + trace
# =============================================================================

def answer_question(
    query: str,
    top_k: int = 5,
    history: Optional[list[dict]] = None,
) -> dict:
    """
    Chạy trọn luồng: resolve follow-up → retrieve (có trace) → generate → validate.

    Returns:
        {
            'answer': str, 'sources': list[dict] (source card đã chuẩn hoá),
            'raw_sources': list[dict], 'trace': list[dict],
            'retrieval_source': str, 'effective_query': str,
            'latency_ms': int, 'retrieval_ms': int, 'generation_ms': int,
            'citations': dict, 'model': str|None, 'provider': str|None,
            'error': str|None, 'error_message': str,
        }
    """
    started = time.perf_counter()
    history = history or []
    trace = _new_trace()

    effective_query = resolve_follow_up(query, history)
    if effective_query != query:
        _set_step(trace, "query", note="Đã ghép ngữ cảnh từ lượt hỏi trước")

    # --- Retrieval -----------------------------------------------------------
    retrieval_start = time.perf_counter()
    try:
        chunks = _instrumented_retrieve(effective_query, top_k, trace)
    except Exception as exc:
        # Retrieval hỏng nghiêm trọng → KHÔNG chạy generation.
        _set_step(trace, "generation", status="idle", note="Bỏ qua do retrieval lỗi")
        return {
            "answer": "",
            "sources": [],
            "raw_sources": [],
            "trace": trace,
            "retrieval_source": "none",
            "effective_query": effective_query,
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "retrieval_ms": int((time.perf_counter() - retrieval_start) * 1000),
            "generation_ms": 0,
            "citations": {"total": 0, "valid": [], "unknown": []},
            "model": None,
            "provider": None,
            "error": "retrieval_failed",
            "error_message": _retrieval_error_message(exc),
        }
    retrieval_ms = int((time.perf_counter() - retrieval_start) * 1000)

    _set_step(trace, "reorder", status="success", count=len(chunks),
              note="front + back[::-1]" if chunks else "Không có chunk")

    # --- Không có evidence → trả sentinel, không gọi LLM ----------------------
    if not chunks:
        _set_step(trace, "generation", status="skipped", note="Không có evidence")
        _set_step(trace, "citation", status="skipped", count=0)
        return {
            "answer": CANNOT_VERIFY,
            "sources": [],
            "raw_sources": [],
            "trace": trace,
            "retrieval_source": "none",
            "effective_query": effective_query,
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "retrieval_ms": retrieval_ms,
            "generation_ms": 0,
            "citations": {"total": 0, "valid": [], "unknown": []},
            "model": None,
            "provider": None,
            "error": None,
            "error_message": "",
        }

    # --- Generation ----------------------------------------------------------
    _set_step(trace, "generation", status="running")
    generation_start = time.perf_counter()
    result = generate_with_citation(
        effective_query,
        context_chunks=chunks,
        conversation_history=history_for_prompt(history),
    )
    generation_ms = int((time.perf_counter() - generation_start) * 1000)

    if result["error"]:
        _set_step(trace, "generation", status="error", ms=generation_ms, note=result["error"])
    else:
        _set_step(
            trace,
            "generation",
            status="success",
            ms=generation_ms,
            note=result.get("model") or "",
        )

    # --- Citation validation -------------------------------------------------
    citations = validate_citations(result["answer"], chunks)
    if result["error"]:
        _set_step(trace, "citation", status="skipped", count=0)
    elif citations["unknown"]:
        _set_step(
            trace,
            "citation",
            status="fallback",
            count=citations["total"],
            note=f"{len(citations['unknown'])} citation không khớp nguồn",
        )
    else:
        _set_step(
            trace,
            "citation",
            status="success",
            count=citations["total"],
            note="Tất cả citation khớp nguồn thật" if citations["total"] else "Không có citation",
        )

    return {
        "answer": result["answer"],
        "sources": [normalize_source(chunk, i) for i, chunk in enumerate(chunks, 1)],
        "raw_sources": chunks,
        "trace": trace,
        "retrieval_source": result["retrieval_source"],
        "effective_query": effective_query,
        "latency_ms": int((time.perf_counter() - started) * 1000),
        "retrieval_ms": retrieval_ms,
        "generation_ms": generation_ms,
        "citations": citations,
        "model": result.get("model"),
        "provider": result.get("provider"),
        "error": result.get("error"),
        "error_message": result["answer"] if result.get("error") else "",
    }


def _retrieval_error_message(exc: Exception) -> str:
    """Thông báo lỗi retrieval bằng tiếng Việt, kèm gợi ý khắc phục."""
    name = type(exc).__name__
    text = str(exc).lower()
    if isinstance(exc, ModuleNotFoundError) or "no module named" in text:
        return (
            "Thiếu thư viện cho retrieval pipeline. Chạy: pip install -r requirements.txt "
            f"(chi tiết kỹ thuật: {name})."
        )
    if "chroma" in text or "collection" in text:
        return (
            "Không mở được vector store ChromaDB. Hãy chạy lại "
            "`python -m src.task4_chunking_indexing` để tạo chroma_db/."
        )
    return f"Retrieval pipeline gặp lỗi ({name}). Xem log console để biết chi tiết."


# =============================================================================
# SYSTEM STATUS — phản ánh trạng thái thật, không hardcode "online"
# =============================================================================

def frontend_build_exists() -> bool:
    """True nếu React component đã được build ra thư mục dist/."""
    return (FRONTEND_DIST / "index.html").is_file()


def get_system_status() -> dict:
    """
    Thu thập trạng thái thật của từng thành phần để hiển thị lên header/sidebar.

    Không bao giờ trả về giá trị API key.
    """
    provider = provider_status()

    chroma = _chroma_status()
    corpus_files = len(list(STANDARDIZED_DIR.rglob("*.md"))) if STANDARDIZED_DIR.exists() else 0

    return {
        "api": {
            "ok": provider["configured"],
            "label": "API key",
            "detail": (
                f"{provider['provider']} · {provider['model']}"
                if provider["configured"]
                else "Chưa cấu hình .env"
            ),
        },
        "chroma": chroma,
        "bm25": {
            "ok": _module_available("rank_bm25"),
            "label": "BM25",
            "detail": "rank-bm25 sẵn sàng" if _module_available("rank_bm25") else "Thiếu gói rank-bm25",
        },
        "rrf": {
            "ok": True,
            "label": "RRF",
            "detail": f"k=60 · ngưỡng cosine {getattr(t9, 'SCORE_THRESHOLD', 0):.2f}",
        },
        "pageindex": _pageindex_status(),
        "corpus": {
            "ok": corpus_files > 0,
            "label": "Corpus",
            "detail": f"{corpus_files} file markdown" if corpus_files else "Chưa có data/standardized/",
        },
        "frontend": {
            "ok": frontend_build_exists(),
            "label": "React UI",
            "detail": "dist/ đã build" if frontend_build_exists() else "Chưa build — dùng giao diện native",
        },
        "score_threshold": float(getattr(t9, "SCORE_THRESHOLD", 0.0)),
    }


def _module_available(name: str) -> bool:
    """Kiểm tra module có import được không mà không thực sự import nội dung nặng."""
    import importlib.util

    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError):
        return False


def _chroma_status() -> dict:
    """Trạng thái ChromaDB: đã cài chưa, collection có bao nhiêu vector."""
    if not _module_available("chromadb"):
        return {
            "ok": False,
            "label": "ChromaDB",
            "detail": "Chưa cài chromadb — Task 5 đang chạy chế độ in-memory",
        }
    # Mở trực tiếp bằng chromadb thay vì phụ thuộc helper của Task 4 — các
    # nhánh khác nhau của nhóm export API khác nhau (có nhánh có
    # get_collection(), có nhánh không), nên đọc thẳng là ổn định nhất.
    try:
        import chromadb

        from .task4_chunking_indexing import CHROMA_DIR, COLLECTION_NAME

        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        count = client.get_collection(COLLECTION_NAME).count()
    except Exception as exc:
        return {"ok": False, "label": "ChromaDB", "detail": f"Không mở được ({type(exc).__name__})"}

    if count == 0:
        return {"ok": False, "label": "ChromaDB", "detail": "Collection rỗng — cần chạy Task 4"}
    return {"ok": True, "label": "ChromaDB", "detail": f"{count} vectors"}


def _pageindex_status() -> dict:
    """Trạng thái PageIndex: dùng API thật hay chế độ vectorless local."""
    import os

    if os.getenv("PAGEINDEX_API_KEY", "").strip():
        return {"ok": True, "label": "PageIndex", "detail": "API key đã cấu hình"}
    if STANDARDIZED_DIR.exists() and any(STANDARDIZED_DIR.rglob("*.md")):
        return {"ok": True, "label": "PageIndex", "detail": "Chế độ vectorless local (theo section)"}
    return {"ok": False, "label": "PageIndex", "detail": "Không có tài liệu để fallback"}


# =============================================================================
# EXPORT
# =============================================================================

def new_conversation_id() -> str:
    """Sinh id hội thoại mới."""
    return uuid.uuid4().hex[:12]


def new_message_id() -> str:
    """Sinh id message mới."""
    return uuid.uuid4().hex[:10]


def export_conversation(messages: list[dict], conversation_id: str, fmt: str = "md") -> str:
    """
    Xuất hội thoại ra Markdown hoặc JSON để nộp bài / lưu lại demo.

    Args:
        fmt: "md" hoặc "json".
    """
    if fmt == "json":
        return json.dumps(
            {
                "conversation_id": conversation_id,
                "exported_at": datetime.now().isoformat(timespec="seconds"),
                "messages": messages,
            },
            ensure_ascii=False,
            indent=2,
        )

    lines = [
        "# University Services RAG Assistant — Lịch sử hội thoại",
        "",
        f"- Mã hội thoại: `{conversation_id}`",
        f"- Xuất lúc: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        f"- Số lượt: {len(messages)}",
        "",
    ]
    for message in messages:
        role = "Người dùng" if message.get("role") == "user" else "Trợ lý"
        lines.append(f"## {role} — {message.get('created_at', '')}")
        lines.append("")
        lines.append(str(message.get("content", "")))
        lines.append("")
        sources = message.get("sources") or []
        if sources:
            lines.append(f"**Nguồn tham khảo ({len(sources)}):**")
            lines.append("")
            for source in sources:
                score = source.get("score")
                score_text = (
                    f"{score:.4f} ({source.get('score_metric')})" if isinstance(score, (int, float))
                    else "Không có điểm"
                )
                lines.append(
                    f"{source.get('rank')}. `{source.get('name')}` — {score_text}"
                    + (f" — {source.get('url')}" if source.get("url") else "")
                )
            lines.append("")
    return "\n".join(lines)


# =============================================================================
# HIGHLIGHT HELPER (dùng chung cho native UI và React component)
# =============================================================================

_STOPWORDS = {
    "là", "và", "của", "cho", "các", "những", "một", "có", "được", "trong", "với",
    "thì", "này", "đó", "nào", "gì", "như", "thế", "để", "khi", "tại", "về",
    "the", "a", "an", "of", "for", "and", "to", "in", "on", "is", "are", "what", "how",
}


def keyword_terms(query: str, limit: int = 12) -> list[str]:
    """
    Rút từ khoá từ câu hỏi để highlight trong excerpt.

    Bỏ stopword và từ quá ngắn; giữ thứ tự xuất hiện, không trùng lặp.
    """
    terms: list[str] = []
    for token in re.findall(r"\w+", str(query or "").lower(), flags=re.UNICODE):
        if len(token) < 3 or token in _STOPWORDS or token in terms:
            continue
        terms.append(token)
        if len(terms) >= limit:
            break
    return terms
