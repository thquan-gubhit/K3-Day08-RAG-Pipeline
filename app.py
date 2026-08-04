"""
University Services RAG Assistant — Streamlit Chatbot (Role 4).

Entrypoint duy nhất của sản phẩm nhóm::

    streamlit run app.py

Kiến trúc:

    Streamlit app.py
        ├── Session state + conversation memory
        ├── src.role4_chat_service.answer_question()
        │       ├── retrieve()                (Task 9 — hybrid + PageIndex fallback)
        │       └── generate_with_citation()  (Task 10 — citation + reordering)
        └── components.university_chat_ui     (React + Tailwind + Motion + Three.js)

Giao diện React là phần *nâng cao*: nếu ``frontend/dist`` chưa được build hoặc
component không nạp được, app tự động chạy bằng giao diện Streamlit native với
đầy đủ chức năng (chat, source inspector, pipeline trace, top_k, memory).

Python chịu trách nhiệm retrieval, LLM, session state, API key, metadata nguồn,
xử lý lỗi và đo latency. React chỉ chịu trách nhiệm trình bày.
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# Thêm project root vào sys.path để import các task từ src/
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.role4_chat_service import (  # noqa: E402
    answer_question,
    export_conversation,
    get_system_status,
    keyword_terms,
    new_conversation_id,
    new_message_id,
    validate_query,
)

# =============================================================================
# PAGE CONFIG — phải gọi trước mọi lệnh Streamlit khác
# =============================================================================

st.set_page_config(
    page_title="University Services RAG Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =============================================================================
# CONSTANTS
# =============================================================================

# Bộ câu hỏi gợi ý đã được đối chiếu THỰC TẾ với corpus hiện tại
# (student-fees-and-charges-guide, scholarship-terms-and-conditions,
# parents-family-guide + 5 bài news): mỗi câu dưới đây đều cho câu trả lời có
# citation hợp lệ. Không đưa vào các câu mà corpus không có bằng chứng
# (ví dụ tiêu chí xét học bổng, đăng ký ký túc xá) — hệ thống sẽ đúng khi trả
# "I cannot verify this information", nhưng câu gợi ý thì không nên hứa sai.
SUGGESTED_QUESTIONS = [
    "Học phí tại RMIT Vietnam được thanh toán như thế nào?",
    "Hạn chót thanh toán học phí là khi nào?",
    "Sinh viên nộp học phí trễ hạn sẽ bị xử lý thế nào?",
    "Sinh viên nhận học bổng phải tuân thủ những điều kiện gì?",
    "Học bổng có thể bị chấm dứt trong trường hợp nào?",
    "Thư viện cung cấp những dịch vụ hỗ trợ nào?",
]

# Trạng thái pipeline → (icon, nhãn tiếng Việt). Luôn kèm text để không phụ
# thuộc riêng vào màu sắc (yêu cầu accessibility).
STATUS_LABELS = {
    "idle": ("○", "Chưa chạy"),
    "running": ("◐", "Đang chạy"),
    "success": ("●", "Hoàn tất"),
    "fallback": ("◆", "Fallback"),
    "skipped": ("–", "Bỏ qua"),
    "error": ("✕", "Lỗi"),
}

# Design tokens — Modern University AI Research Console.
CUSTOM_CSS = """
<style>
:root {
    --bg-primary: #07111F;
    --bg-secondary: #0B1728;
    --card-bg: rgba(16, 30, 49, 0.78);
    --border: rgba(148, 163, 184, 0.14);
    --cyan: #22D3EE;
    --indigo: #6366F1;
    --violet: #A78BFA;
    --success: #34D399;
    --warning: #FBBF24;
    --danger: #FB7185;
    --text: #F8FAFC;
    --text-muted: #94A3B8;
}
.stApp {
    background:
        radial-gradient(1100px 520px at 12% -8%, rgba(99, 102, 241, 0.16), transparent 60%),
        radial-gradient(900px 460px at 88% 0%, rgba(34, 211, 238, 0.12), transparent 62%),
        var(--bg-primary);
    color: var(--text);
}
section[data-testid="stSidebar"] {
    background: var(--bg-secondary);
    border-right: 1px solid var(--border);
}
.rag-header {
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 18px 22px;
    margin-bottom: 14px;
    background:
        linear-gradient(120deg, rgba(34,211,238,.14), rgba(99,102,241,.14) 46%, rgba(167,139,250,.14)),
        var(--card-bg);
    background-size: 220% 100%;
    animation: ragGradient 22s ease infinite;
}
@keyframes ragGradient {
    0%   { background-position: 0% 50%; }
    50%  { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}
.rag-header h1 {
    font-size: 1.32rem;
    margin: 0 0 2px 0;
    letter-spacing: -0.01em;
    color: var(--text);
}
.rag-header p { margin: 0; color: var(--text-muted); font-size: 0.86rem; }
.rag-badges { display: flex; flex-wrap: wrap; gap: 7px; margin-top: 12px; }
.rag-badge {
    display: inline-flex; align-items: center; gap: 6px;
    font-size: 0.73rem; padding: 3px 11px; border-radius: 999px;
    border: 1px solid var(--border); background: rgba(8, 17, 30, 0.6);
    color: var(--text-muted); white-space: nowrap;
}
.rag-badge.ok { border-color: rgba(52, 211, 153, 0.42); color: var(--success); }
.rag-badge.warn { border-color: rgba(251, 191, 36, 0.42); color: var(--warning); }
.rag-panel {
    border: 1px solid var(--border);
    border-radius: 14px;
    background: var(--card-bg);
    padding: 13px 15px;
    margin-bottom: 11px;
    transition: border-color .18s ease, transform .18s ease;
}
.rag-panel:hover { border-color: rgba(34, 211, 238, 0.34); transform: translateY(-1px); }
.rag-panel-title {
    font-size: 0.7rem; text-transform: uppercase; letter-spacing: .1em;
    color: var(--text-muted); margin-bottom: 9px;
}
.rag-source-head { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
.rag-rank {
    background: linear-gradient(135deg, var(--cyan), var(--indigo));
    color: #04121f; font-weight: 700; font-size: .72rem;
    border-radius: 7px; padding: 1px 8px;
}
.rag-source-name { font-weight: 600; font-size: .87rem; color: var(--text); word-break: break-word; }
.rag-meta { font-size: .74rem; color: var(--text-muted); margin-top: 5px; line-height: 1.65; }
.rag-chip {
    display: inline-block; font-size: .68rem; padding: 1px 8px; border-radius: 6px;
    border: 1px solid var(--border); color: var(--text-muted); margin-right: 5px;
}
.rag-chip.semantic { border-color: rgba(34,211,238,.45); color: var(--cyan); }
.rag-chip.pageindex { border-color: rgba(167,139,250,.45); color: var(--violet); }
.rag-chip.hybrid { border-color: rgba(99,102,241,.45); color: #A5B4FC; }
.rag-step {
    display: flex; align-items: center; gap: 9px;
    padding: 6px 9px; border-radius: 9px; font-size: .78rem;
    border: 1px solid transparent; margin-bottom: 3px;
}
.rag-step.success { background: rgba(52,211,153,.09); border-color: rgba(52,211,153,.26); }
.rag-step.fallback { background: rgba(167,139,250,.11); border-color: rgba(167,139,250,.3); }
.rag-step.error { background: rgba(251,113,133,.11); border-color: rgba(251,113,133,.3); }
.rag-step.skipped, .rag-step.idle { background: rgba(148,163,184,.05); }
.rag-step-name { flex: 1; color: var(--text); }
.rag-step-meta { color: var(--text-muted); font-size: .71rem; white-space: nowrap; }
/* Citation được render dạng inline code (an toàn, không dùng HTML từ LLM) */
[data-testid="stChatMessage"] code {
    background: rgba(34, 211, 238, 0.13);
    border: 1px solid rgba(34, 211, 238, 0.28);
    color: var(--cyan);
    border-radius: 5px; padding: 1px 5px; font-size: .84em;
}
[data-testid="stChatMessage"] { animation: ragFade .28s ease both; }
@keyframes ragFade { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
.rag-empty {
    border: 1px dashed var(--border); border-radius: 16px;
    padding: 30px 22px; text-align: center; color: var(--text-muted);
    background: var(--card-bg);
}
.rag-orb {
    width: 116px; height: 116px; margin: 0 auto 16px auto; border-radius: 50%;
    background: radial-gradient(circle at 34% 30%, rgba(34,211,238,.85), rgba(99,102,241,.5) 45%, rgba(7,17,31,0) 72%);
    animation: ragPulse 4.5s ease-in-out infinite;
}
@keyframes ragPulse {
    0%,100% { transform: scale(1); opacity: .85; }
    50% { transform: scale(1.07); opacity: 1; }
}
:focus-visible { outline: 2px solid var(--cyan); outline-offset: 2px; }
@media (prefers-reduced-motion: reduce) {
    .rag-header, .rag-orb, [data-testid="stChatMessage"] { animation: none !important; }
    .rag-panel { transition: none !important; }
}
@media (max-width: 900px) {
    .rag-header h1 { font-size: 1.08rem; }
    .rag-orb { width: 84px; height: 84px; }
}
</style>
"""

REDUCED_MOTION_CSS = """
<style>
.rag-header, .rag-orb, [data-testid="stChatMessage"] { animation: none !important; }
.rag-panel { transition: none !important; }
</style>
"""


# =============================================================================
# SESSION STATE
# =============================================================================

def init_session_state() -> None:
    """
    Khởi tạo session state một lần duy nhất.

    Streamlit chạy lại toàn bộ script sau mỗi tương tác, nên mọi giá trị cần
    bền vững phải nằm trong ``st.session_state`` và chỉ được set khi CHƯA tồn
    tại — nếu không, lịch sử chat sẽ bị xoá ở mỗi lần rerun.
    """
    defaults = {
        "messages": [],
        "conversation_id": new_conversation_id(),
        "top_k": 5,
        "last_sources": [],
        "last_pipeline_trace": [],
        "is_generating": False,
        "ui_mode": "auto",
        "pending_query": None,
        "last_event_nonce": None,
        "show_scores": True,
        "show_trace": True,
        "reduced_motion": False,
        "selected_source_id": None,
        "notice": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def reset_conversation(keep_settings: bool = True) -> None:
    """Bắt đầu hội thoại mới: xoá lịch sử, nguồn và trace của lượt trước."""
    st.session_state.messages = []
    st.session_state.conversation_id = new_conversation_id()
    st.session_state.last_sources = []
    st.session_state.last_pipeline_trace = []
    st.session_state.selected_source_id = None
    st.session_state.pending_query = None
    st.session_state.is_generating = False
    if not keep_settings:
        st.session_state.top_k = 5


def append_message(role: str, content: str, **extra) -> dict:
    """Thêm 1 message vào lịch sử theo schema thống nhất."""
    message = {
        "id": new_message_id(),
        "role": role,
        "content": content,
        "created_at": datetime.now().strftime("%H:%M:%S"),
        "sources": extra.get("sources", []),
        "latency_ms": extra.get("latency_ms"),
        "error": extra.get("error"),
        "citations": extra.get("citations"),
        "retrieval_source": extra.get("retrieval_source"),
        "model": extra.get("model"),
    }
    st.session_state.messages.append(message)
    return message


# =============================================================================
# RENDER HELPERS (Streamlit native)
# =============================================================================

_CODE_FENCE = re.compile(r"(```.*?```|`[^`\n]*`)", re.DOTALL)
_CITATION = re.compile(r"\[[^\[\]\n]{1,160}?,\s*[^\[\]\n]{1,40}?\]")


def highlight_citations(answer: str) -> str:
    """
    Bọc citation ``[Nguồn, Năm]`` bằng inline code để hiển thị nổi bật.

    Dùng markdown (không phải HTML) nên nội dung do LLM sinh ra không bao giờ
    được render như HTML — tránh hoàn toàn rủi ro injection từ câu trả lời.
    Bỏ qua phần nằm trong code block để không phá cú pháp code.
    """
    parts = _CODE_FENCE.split(answer or "")
    for i, part in enumerate(parts):
        if part.startswith("`"):
            continue
        parts[i] = _CITATION.sub(lambda m: f"`{m.group(0)}`", part)
    return "".join(parts)


def highlight_terms(text: str, terms: list[str]) -> str:
    """In đậm các từ khoá của câu hỏi trong excerpt (markdown, không HTML)."""
    if not terms:
        return text
    pattern = re.compile(
        "(" + "|".join(re.escape(t) for t in sorted(terms, key=len, reverse=True)) + ")",
        re.IGNORECASE,
    )
    return pattern.sub(lambda m: f"**{m.group(0)}**", text)


def render_header(status: dict) -> None:
    """Header với tên hệ thống và badge trạng thái THẬT của từng thành phần."""
    badges = []
    for key in ("chroma", "bm25", "rrf", "pageindex", "api"):
        item = status.get(key)
        if not item:
            continue
        css = "ok" if item["ok"] else "warn"
        mark = "✓" if item["ok"] else "!"
        badges.append(
            f'<span class="rag-badge {css}" title="{escape_attr(item["detail"])}">'
            f'{mark} {escape_attr(item["label"])}</span>'
        )
    ready = status["corpus"]["ok"]
    badges.insert(
        0,
        f'<span class="rag-badge {"ok" if ready else "warn"}">'
        f'{"✓ Pipeline sẵn sàng" if ready else "! Thiếu dữ liệu corpus"}</span>',
    )
    st.markdown(
        f"""
<div class="rag-header">
    <h1>🎓 University Services RAG Assistant</h1>
    <p>Hybrid Retrieval • Citation-grounded</p>
    <div class="rag-badges">{''.join(badges)}</div>
</div>
""",
        unsafe_allow_html=True,
    )


def escape_attr(value: str) -> str:
    """Escape chuỗi trước khi nhúng vào HTML tĩnh do chính app tạo ra."""
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_message(message: dict, show_sources: bool = True) -> None:
    """Render 1 message (user hoặc assistant) kèm nguồn và metadata."""
    with st.chat_message(message["role"]):
        if message["role"] == "assistant":
            st.markdown(highlight_citations(message["content"]))
        else:
            st.markdown(message["content"])

        meta_bits = [message.get("created_at", "")]
        if message.get("latency_ms") is not None:
            meta_bits.append(f"{message['latency_ms']} ms")
        if message.get("sources"):
            meta_bits.append(f"{len(message['sources'])} nguồn")
        citations = message.get("citations") or {}
        if citations.get("total"):
            meta_bits.append(f"{citations['total']} citation")
        if message.get("model"):
            meta_bits.append(str(message["model"]))
        st.caption(" · ".join(b for b in meta_bits if b))

        if citations.get("unknown"):
            st.warning(
                "Câu trả lời chứa citation không khớp nguồn đã truy xuất: "
                + ", ".join(citations["unknown"][:3])
            )

        if show_sources and message.get("sources"):
            with st.expander(f"📚 Nguồn đã dùng ({len(message['sources'])})"):
                render_sources(message["sources"], message.get("query_terms", []))


def render_sources(sources: list[dict], terms: list[str]) -> None:
    """Source inspector — mọi trường đều lấy từ metadata thật."""
    if not sources:
        st.caption("Không có nguồn nào được sử dụng.")
        return

    for source in sources:
        origin = (source.get("origin") or "hybrid").lower()
        chip_class = origin if origin in ("hybrid", "pageindex", "semantic") else "hybrid"
        score = source.get("score")
        if isinstance(score, (int, float)):
            score_text = f"{score:.4f} · {escape_attr(source.get('score_metric', ''))}"
        else:
            score_text = "Không có điểm"

        meta_lines = [
            f'<span class="rag-chip {chip_class}">{escape_attr(source.get("retrieval_type") or origin)}</span>'
            f'<span class="rag-chip">{escape_attr(source.get("doc_type") or "không rõ loại")}</span>',
            f"Điểm: {score_text}",
            f"Năm: {escape_attr(source.get('year') or 'n.d.')}",
        ]
        if source.get("chunk_id"):
            meta_lines.append(f"Chunk: {escape_attr(source['chunk_id'])}")
        if source.get("date"):
            meta_lines.append(f"Ngày: {escape_attr(source['date'])}")

        st.markdown(
            f"""
<div class="rag-panel">
    <div class="rag-source-head">
        <span class="rag-rank">#{source.get('rank')}</span>
        <span class="rag-source-name">{escape_attr(source.get('title') or source.get('name'))}</span>
    </div>
    <div class="rag-meta">{'<br>'.join(meta_lines)}</div>
</div>
""",
            unsafe_allow_html=True,
        )

        excerpt = source.get("excerpt") or ""
        if excerpt:
            with st.expander(f"Trích đoạn #{source.get('rank')}", expanded=False):
                st.markdown(highlight_terms(excerpt, terms))
                st.code(source.get("content", "")[:2000], language=None)
        if source.get("url"):
            st.markdown(f"[🔗 Mở nguồn gốc]({source['url']})")


def render_pipeline_trace(trace: list[dict]) -> None:
    """Pipeline trace — chỉ hiển thị dữ liệu đo được thật từ lần chạy gần nhất."""
    if not trace:
        st.caption("Chưa có lượt hỏi nào. Pipeline trace sẽ hiện sau câu hỏi đầu tiên.")
        return

    for step in trace:
        icon, label = STATUS_LABELS.get(step["status"], ("○", step["status"]))
        meta = []
        if step.get("count") is not None:
            meta.append(f"{step['count']} docs")
        if step.get("ms") is not None:
            meta.append(f"{step['ms']} ms")
        meta.append(label)
        st.markdown(
            f"""
<div class="rag-step {step['status']}">
    <span aria-hidden="true">{icon}</span>
    <span class="rag-step-name">{escape_attr(step['label'])}</span>
    <span class="rag-step-meta">{escape_attr(' · '.join(meta))}</span>
</div>
""",
            unsafe_allow_html=True,
        )
        if step.get("note"):
            st.caption(f"↳ {step['note']}")


def render_empty_state() -> None:
    """Empty state có visual nhẹ khi chưa có hội thoại nào."""
    st.markdown(
        """
<div class="rag-empty">
    <div class="rag-orb" role="img" aria-label="Biểu tượng lõi tri thức"></div>
    <div style="font-size:1rem;color:#F8FAFC;margin-bottom:6px;">
        Bắt đầu bằng một câu hỏi về dịch vụ đại học
    </div>
    <div style="font-size:.84rem;">
        Hệ thống tìm kiếm song song bằng ChromaDB (ngữ nghĩa) và BM25 (từ khoá),
        hợp nhất bằng RRF, và chỉ trả lời dựa trên tài liệu tìm được.
    </div>
</div>
""",
        unsafe_allow_html=True,
    )


# =============================================================================
# SIDEBAR
# =============================================================================

def render_sidebar(status: dict) -> None:
    """Sidebar: trạng thái hệ thống, câu hỏi gợi ý, thiết lập, hành động."""
    with st.sidebar:
        st.title("🎓 University Services RAG")
        st.caption("Trợ lý hỏi đáp học phí • học bổng • ký túc xá • thư viện")

        st.divider()
        st.subheader("📡 Trạng thái hệ thống")
        for key in ("api", "chroma", "bm25", "pageindex", "corpus", "frontend"):
            item = status.get(key)
            if not item:
                continue
            icon = "✅" if item["ok"] else "⚠️"
            st.markdown(f"{icon} **{item['label']}** — {item['detail']}")
        st.caption(
            f"Ngưỡng fallback (chỉ đọc): cosine < {status['score_threshold']:.2f} → PageIndex"
        )
        if not status["api"]["ok"]:
            st.info(
                "Chưa có API key nên phần sinh câu trả lời bị tắt. "
                "Tạo file `.env` ở thư mục gốc:\n\n"
                "```\nOPENROUTER_API_KEY=sk-or-v1-...\n```\n"
                "Retrieval và source inspector vẫn hoạt động bình thường."
            )

        st.divider()
        st.subheader("💡 Câu hỏi gợi ý")
        for i, question in enumerate(SUGGESTED_QUESTIONS):
            if st.button(
                question,
                use_container_width=True,
                key=f"suggestion_{i}",
                disabled=st.session_state.is_generating,
            ):
                st.session_state.pending_query = question
                st.rerun()

        st.divider()
        st.subheader("⚙️ Thiết lập")
        st.session_state.top_k = st.slider(
            "Số chunks retrieval (top_k)",
            min_value=3,
            max_value=10,
            value=st.session_state.top_k,
            help="Số lượng đoạn tài liệu đưa vào context cho LLM.",
        )
        st.session_state.show_scores = st.toggle(
            "Hiển thị điểm số", value=st.session_state.show_scores
        )
        st.session_state.show_trace = st.toggle(
            "Hiển thị pipeline trace", value=st.session_state.show_trace
        )
        st.session_state.reduced_motion = st.toggle(
            "Giảm chuyển động", value=st.session_state.reduced_motion
        )

        ui_options = ["auto", "native"]
        if status["frontend"]["ok"]:
            ui_options = ["auto", "react", "native"]
        st.session_state.ui_mode = st.selectbox(
            "Giao diện",
            ui_options,
            index=ui_options.index(st.session_state.ui_mode)
            if st.session_state.ui_mode in ui_options
            else 0,
            help="auto: dùng React nếu đã build, ngược lại dùng Streamlit native.",
        )

        st.divider()
        st.subheader("🗂️ Hội thoại")
        st.caption(f"Mã: `{st.session_state.conversation_id}` · {len(st.session_state.messages)} lượt")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("🆕 Cuộc trò chuyện mới", use_container_width=True):
                reset_conversation()
                st.rerun()
        with col_b:
            if st.button("🗑️ Xóa lịch sử", use_container_width=True):
                reset_conversation()
                st.rerun()

        if st.session_state.messages:
            st.download_button(
                "⬇️ Export Markdown",
                data=export_conversation(
                    st.session_state.messages, st.session_state.conversation_id, "md"
                ),
                file_name=f"conversation_{st.session_state.conversation_id}.md",
                mime="text/markdown",
                use_container_width=True,
            )
            st.download_button(
                "⬇️ Export JSON",
                data=export_conversation(
                    st.session_state.messages, st.session_state.conversation_id, "json"
                ),
                file_name=f"conversation_{st.session_state.conversation_id}.json",
                mime="application/json",
                use_container_width=True,
            )

        st.divider()
        st.caption("**Kiến trúc:** Semantic (ChromaDB) + BM25 → RRF → PageIndex fallback → Reorder → LLM có citation")


# =============================================================================
# QUERY PROCESSING
# =============================================================================

def process_pending_query() -> None:
    """
    Xử lý câu hỏi đang chờ: validate → retrieve → generate → lưu kết quả.

    Chỉ chạy khi có ``pending_query``; luôn clear cờ trước khi xử lý để một lần
    rerun không thể kích hoạt hai lần generation (chống double-submit).
    """
    raw_query = st.session_state.pending_query
    st.session_state.pending_query = None
    if not raw_query:
        return

    is_valid, query, error_message = validate_query(raw_query)
    if not is_valid:
        st.session_state.notice = error_message
        st.session_state.is_generating = False
        return

    history = [
        {"role": m["role"], "content": m["content"]}
        for m in st.session_state.messages
        if not m.get("error")
    ]
    append_message("user", query)

    with st.chat_message("user"):
        st.markdown(query)

    with st.chat_message("assistant"):
        with st.spinner("Đang truy xuất tài liệu và tổng hợp câu trả lời…"):
            try:
                result = answer_question(query, top_k=st.session_state.top_k, history=history)
            except Exception as exc:  # noqa: BLE001 - chặn mọi lỗi để app không chết
                print(f"[app] Lỗi không mong đợi khi xử lý câu hỏi: {type(exc).__name__}: {exc}")
                append_message(
                    "assistant",
                    "Đã xảy ra lỗi ngoài dự kiến khi xử lý câu hỏi. "
                    "Hãy thử lại; nếu vẫn lỗi, kiểm tra log ở console.",
                    error="unexpected",
                )
                st.session_state.is_generating = False
                return

    if result["error"] == "retrieval_failed":
        append_message("assistant", result["error_message"], error=result["error"])
        st.session_state.is_generating = False
        return

    append_message(
        "assistant",
        result["answer"],
        sources=result["sources"],
        latency_ms=result["latency_ms"],
        error=result["error"],
        citations=result["citations"],
        retrieval_source=result["retrieval_source"],
        model=result["model"],
    )
    st.session_state.messages[-1]["query_terms"] = keyword_terms(query)
    st.session_state.last_sources = result["sources"]
    st.session_state.last_pipeline_trace = result["trace"]
    st.session_state.selected_source_id = None
    st.session_state.is_generating = False


# =============================================================================
# UI MODES
# =============================================================================

def render_native_ui(status: dict) -> None:
    """Giao diện Streamlit native — luôn khả dụng, không phụ thuộc React build."""
    render_header(status)

    chat_col, evidence_col = st.columns([2.1, 1], gap="medium")

    with chat_col:
        if not st.session_state.messages and not st.session_state.pending_query:
            render_empty_state()
        for message in st.session_state.messages:
            render_message(message)

        if st.session_state.pending_query:
            st.session_state.is_generating = True
            process_pending_query()
            st.rerun()

    with evidence_col:
        st.markdown('<div class="rag-panel-title">Evidence panel</div>', unsafe_allow_html=True)
        with st.expander("📚 Nguồn của câu trả lời gần nhất", expanded=True):
            terms = []
            for message in reversed(st.session_state.messages):
                if message.get("query_terms"):
                    terms = message["query_terms"]
                    break
            render_sources(st.session_state.last_sources, terms)

        if st.session_state.show_trace:
            with st.expander("🔎 Pipeline trace", expanded=True):
                render_pipeline_trace(st.session_state.last_pipeline_trace)


def render_react_ui(status: dict) -> bool:
    """
    Giao diện React custom component.

    Returns:
        True nếu component render được; False để caller fallback sang native.
    """
    try:
        from components.university_chat_ui import university_chat_ui
    except ImportError as exc:
        print(f"[app] Không import được custom component: {exc}")
        return False

    event = university_chat_ui(
        messages=compact_messages(st.session_state.messages),
        sources=compact_sources(st.session_state.last_sources),
        pipeline_trace=st.session_state.last_pipeline_trace,
        settings={
            "topK": st.session_state.top_k,
            "showScores": st.session_state.show_scores,
            "showTrace": st.session_state.show_trace,
            "reducedMotion": st.session_state.reduced_motion,
        },
        status=status,
        suggested_questions=SUGGESTED_QUESTIONS,
        is_generating=st.session_state.is_generating,
        selected_source_id=st.session_state.selected_source_id,
        key=f"chat_ui_{st.session_state.conversation_id}",
    )

    if event is None and not st.session_state.messages and not st.session_state.pending_query:
        # Component chưa gửi giá trị nào — bình thường ở lần render đầu tiên.
        pass

    if handle_component_event(event):
        st.rerun()

    if st.session_state.pending_query:
        st.session_state.is_generating = True
        with st.status("Đang xử lý câu hỏi…", expanded=False):
            process_pending_query()
        st.rerun()

    return True


def handle_component_event(event) -> bool:
    """
    Xử lý sự kiện từ React component.

    Chống xử lý trùng bằng ``nonce``: Streamlit trả lại giá trị cũ ở MỌI lần
    rerun sau đó, nên nếu không so nonce thì một lần submit sẽ chạy vô hạn.

    Returns:
        True nếu có thay đổi state cần rerun.
    """
    if not isinstance(event, dict):
        return False

    nonce = event.get("nonce")
    event_type = event.get("type")
    if not nonce or not isinstance(event_type, str):
        return False
    if nonce == st.session_state.last_event_nonce:
        return False
    st.session_state.last_event_nonce = nonce

    if event_type in ("submit_query", "select_suggestion"):
        query = event.get("query")
        if isinstance(query, str) and query.strip():
            st.session_state.pending_query = query.strip()
            return True
        return False

    if event_type == "new_conversation":
        reset_conversation()
        return True

    if event_type == "clear_history":
        reset_conversation()
        return True

    if event_type == "select_source":
        source_id = event.get("sourceId")
        st.session_state.selected_source_id = source_id if isinstance(source_id, str) else None
        return True

    if event_type == "update_settings":
        payload = event.get("payload")
        if not isinstance(payload, dict):
            return False
        top_k = payload.get("topK")
        if isinstance(top_k, int) and 3 <= top_k <= 10:
            st.session_state.top_k = top_k
        for flag, key in (
            ("showScores", "show_scores"),
            ("showTrace", "show_trace"),
            ("reducedMotion", "reduced_motion"),
        ):
            if isinstance(payload.get(flag), bool):
                st.session_state[key] = payload[flag]
        return True

    # Sự kiện lạ (phiên bản frontend cũ/mới) — bỏ qua an toàn.
    print(f"[app] Bỏ qua sự kiện không nhận dạng được: {event_type}")
    return False


def compact_messages(messages: list[dict]) -> list[dict]:
    """Rút gọn message trước khi gửi sang React (không kèm nội dung source dài)."""
    return [
        {
            "id": m["id"],
            "role": m["role"],
            "content": m["content"],
            "createdAt": m.get("created_at", ""),
            "latencyMs": m.get("latency_ms"),
            "sourceCount": len(m.get("sources") or []),
            "citationCount": (m.get("citations") or {}).get("total", 0),
            "unknownCitations": (m.get("citations") or {}).get("unknown", []),
            "retrievalSource": m.get("retrieval_source"),
            "model": m.get("model"),
            "error": m.get("error"),
        }
        for m in messages[-40:]
    ]


def compact_sources(sources: list[dict]) -> list[dict]:
    """Giới hạn độ dài excerpt gửi sang React để iframe không phải nhận payload lớn."""
    compact = []
    for source in sources:
        item = {k: v for k, v in source.items() if k != "content"}
        item["excerpt"] = (source.get("excerpt") or "")[:600]
        compact.append(item)
    return compact


# =============================================================================
# MAIN
# =============================================================================

def main() -> None:
    """Điểm vào chính của ứng dụng Streamlit."""
    init_session_state()

    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    if st.session_state.reduced_motion:
        st.markdown(REDUCED_MOTION_CSS, unsafe_allow_html=True)

    try:
        status = get_system_status()
    except Exception as exc:  # noqa: BLE001
        print(f"[app] Không lấy được trạng thái hệ thống: {type(exc).__name__}: {exc}")
        st.error(
            "Không kiểm tra được trạng thái hệ thống. "
            "Hãy chạy `pip install -r requirements.txt` rồi khởi động lại app."
        )
        return

    render_sidebar(status)

    if st.session_state.notice:
        st.warning(st.session_state.notice)
        st.session_state.notice = None

    # Chọn chế độ giao diện. React chỉ là enhancement — mọi lỗi đều rơi về native.
    use_react = st.session_state.ui_mode in ("auto", "react") and status["frontend"]["ok"]
    if st.session_state.ui_mode == "native":
        use_react = False

    rendered = False
    if use_react:
        try:
            rendered = render_react_ui(status)
        except Exception as exc:  # noqa: BLE001
            print(f"[app] Custom component lỗi, chuyển sang native: {type(exc).__name__}: {exc}")
            st.warning("Giao diện React không tải được — đang dùng giao diện Streamlit native.")
            rendered = False

    if not rendered:
        render_native_ui(status)

    # Composer luôn ở tầng ngoài cùng để Streamlit ghim xuống đáy trang.
    user_input = st.chat_input(
        "Hỏi về học phí, học bổng, ký túc xá, đăng ký học phần…",
        disabled=st.session_state.is_generating,
        max_chars=500,
    )
    if user_input:
        st.session_state.pending_query = user_input
        st.rerun()


main()
