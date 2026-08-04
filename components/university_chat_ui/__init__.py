"""
Streamlit Custom Component v1 — University Chat UI (React + TypeScript + Vite).

Hai chế độ nạp frontend:

* **Production (mặc định)** — nạp static build từ ``frontend/dist/``.
  Build bằng::

      cd components/university_chat_ui/frontend
      npm install
      npm run build

* **Development** — đặt biến môi trường ``UNIVERSITY_CHAT_UI_DEV=1`` rồi chạy
  ``npm run dev``; component sẽ trỏ tới Vite dev server (mặc định
  ``http://localhost:5173``, override bằng ``UNIVERSITY_CHAT_UI_DEV_URL``).

Nếu ``dist/`` chưa tồn tại, ``frontend_build_exists()`` trả ``False`` và
``app.py`` tự chuyển sang giao diện Streamlit native thay vì crash.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

import streamlit.components.v1 as components

_COMPONENT_NAME = "university_chat_ui"
_FRONTEND_DIR = Path(__file__).parent / "frontend"
_BUILD_DIR = _FRONTEND_DIR / "dist"
_DEV_URL_DEFAULT = "http://localhost:5173"

# Cache instance declare_component để không khai báo lại mỗi lần Streamlit rerun.
_component_func: Optional[Any] = None
_declared_mode: Optional[str] = None


def frontend_build_exists() -> bool:
    """True nếu bundle production đã được Vite build ra ``frontend/dist/``."""
    return (_BUILD_DIR / "index.html").is_file()


def _dev_mode() -> bool:
    """True khi bật chế độ dev để trỏ tới Vite dev server."""
    return os.getenv("UNIVERSITY_CHAT_UI_DEV", "").strip().lower() in ("1", "true", "yes")


def _get_component() -> Optional[Any]:
    """
    Khai báo (hoặc lấy lại) component. Trả ``None`` nếu chưa build và cũng không
    ở chế độ dev — caller phải fallback sang giao diện native.
    """
    global _component_func, _declared_mode

    mode = "dev" if _dev_mode() else "release"
    if _component_func is not None and _declared_mode == mode:
        return _component_func

    if mode == "dev":
        url = os.getenv("UNIVERSITY_CHAT_UI_DEV_URL", "").strip() or _DEV_URL_DEFAULT
        _component_func = components.declare_component(_COMPONENT_NAME, url=url)
    else:
        if not frontend_build_exists():
            return None
        _component_func = components.declare_component(_COMPONENT_NAME, path=str(_BUILD_DIR))

    _declared_mode = mode
    return _component_func


def university_chat_ui(
    *,
    messages: list[dict],
    sources: list[dict],
    pipeline_trace: list[dict],
    settings: dict,
    status: dict,
    suggested_questions: list[str],
    is_generating: bool = False,
    selected_source_id: Optional[str] = None,
    height: int = 720,
    key: str = "university_chat_ui",
) -> Optional[dict]:
    """
    Render chat UI bằng React component và nhận sự kiện người dùng gửi ngược lại.

    Args:
        messages: Lịch sử chat đã rút gọn (không kèm nội dung source dài).
        sources: Source card của câu trả lời gần nhất.
        pipeline_trace: Các bước pipeline kèm trạng thái/thời gian thật.
        settings: Cấu hình UI hiện tại (top_k, show_scores, reduced_motion...).
        status: Trạng thái hệ thống (API key, ChromaDB, PageIndex...).
        suggested_questions: Danh sách câu hỏi gợi ý.
        is_generating: Đang sinh câu trả lời hay không.
        selected_source_id: Source đang được chọn để highlight.
        height: Chiều cao iframe (px).
        key: Streamlit widget key.

    Returns:
        Dict sự kiện ``{'nonce': str, 'type': str, ...}`` hoặc ``None``.
        Caller phải tự chống xử lý trùng bằng ``nonce`` (Streamlit trả lại giá
        trị cũ ở mọi lần rerun sau đó).
    """
    component = _get_component()
    if component is None:
        return None

    value = component(
        messages=messages,
        sources=sources,
        pipelineTrace=pipeline_trace,
        settings=settings,
        status=status,
        suggestedQuestions=suggested_questions,
        isGenerating=is_generating,
        selectedSourceId=selected_source_id,
        height=height,
        key=key,
        default=None,
    )
    return value if isinstance(value, dict) else None
