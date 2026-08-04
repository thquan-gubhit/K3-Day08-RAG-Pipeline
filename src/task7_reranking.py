"""
Task 7 — Reranking Module.

Chọn 1 trong các phương pháp:
    - Cross-encoder reranker: Jina Reranker v2 (multilingual) hoặc Qwen3-Reranker
    - MMR (Maximal Marginal Relevance): tự implement
    - RRF (Reciprocal Rank Fusion): tự implement — khuyến nghị vì không cần API key

Nếu dùng MMR hoặc RRF, đảm bảo hiểu và giải thích được cơ chế.

Lưu ý quan trọng về RRF (sẽ dùng lại ở Task 9): điểm RRF fused CHỈ phụ thuộc thứ hạng,
không phải độ tương đồng thật. Top-1 sau khi fuse luôn xấp xỉ 1/(k+1) ≈ 0.0164 (k=60),
bất kể nội dung đó có thật sự liên quan đến câu hỏi hay không. Đừng dùng điểm RRF để
quyết định fallback ở Task 9 — xem ghi chú ở đó.
"""

from typing import Optional


def rerank_cross_encoder(
    query: str, candidates: list[dict], top_k: int = 5
) -> list[dict]:
    """
    Rerank candidates sử dụng cross-encoder model.
    Hỗ trợ Jina Reranker API hoặc tự động lui về RRF/Semantic score nếu thiếu API key.
    """
    if not candidates or top_k <= 0:
        return []
    
    import os
    import requests
    jina_key = os.getenv("JINA_API_KEY")
    if jina_key:
        try:
            response = requests.post(
                "https://api.jina.ai/v1/rerank",
                headers={"Authorization": f"Bearer {jina_key}"},
                json={
                    "model": "jina-reranker-v2-base-multilingual",
                    "query": query,
                    "documents": [c.get("content", "") for c in candidates],
                    "top_n": top_k
                },
                timeout=5.0
            )
            if response.status_code == 200:
                reranked = response.json().get("results", [])
                output = []
                for r in reranked:
                    idx = r["index"]
                    item = candidates[idx].copy()
                    item["score"] = float(r["relevance_score"])
                    output.append(item)
                return output[:top_k]
        except Exception:
            pass

    # Fallback nội bộ nếu không có key hoặc đứt kết nối mạng (dùng từ khóa & điểm sẵn có)
    import re
    q_terms = set(re.findall(r"\w+", query.lower()))
    res = []
    for c in candidates:
        content = c.get("content", "")
        c_terms = set(re.findall(r"\w+", content.lower()))
        overlap = len(q_terms & c_terms) / max(1, len(q_terms))
        orig_score = float(c.get("score", 0.0))
        new_score = 0.6 * orig_score + 0.4 * overlap
        res.append({**c, "score": new_score})
    return sorted(res, key=lambda x: x["score"], reverse=True)[:top_k]


def rerank_mmr(
    query_embedding: list[float],
    candidates: list[dict],
    top_k: int = 5,
    lambda_param: float = 0.7,
) -> list[dict]:
    """
    Maximal Marginal Relevance — chọn candidates vừa relevant vừa diverse.

    MMR = λ * sim(query, doc) - (1-λ) * max(sim(doc, selected_docs))
    """
    if not candidates or top_k <= 0:
        return []

    import math
    def cosine_sim(v1, v2):
        if not v1 or not v2 or len(v1) != len(v2):
            return 0.0
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        return dot / (norm1 * norm2) if (norm1 * norm2) > 0 else 0.0

    # Kiểm tra và nén embedding nếu candidate chưa có
    items = []
    need_encode = [c for c in candidates if "embedding" not in c or not c["embedding"]]
    if need_encode:
        try:
            from .task4_chunking_indexing import get_embedding_model
            model = get_embedding_model()
            vecs = model.encode([c.get("content", "") for c in need_encode])
            for c, v in zip(need_encode, vecs):
                c["embedding"] = v.tolist() if hasattr(v, "tolist") else list(v)
        except Exception:
            for c in need_encode:
                c["embedding"] = [1.0] * len(query_embedding) if query_embedding else [1.0]

    selected = []
    remaining = list(range(len(candidates)))

    while len(selected) < min(top_k, len(candidates)) and remaining:
        best_idx = None
        best_score = float("-inf")

        for idx in remaining:
            doc_vec = candidates[idx].get("embedding", [])
            relevance = cosine_sim(query_embedding, doc_vec)

            max_sim_to_selected = 0.0
            for sel_idx in selected:
                sel_vec = candidates[sel_idx].get("embedding", [])
                sim = cosine_sim(doc_vec, sel_vec)
                if sim > max_sim_to_selected:
                    max_sim_to_selected = sim

            mmr_score = lambda_param * relevance - (1.0 - lambda_param) * max_sim_to_selected
            if mmr_score > best_score:
                best_score = mmr_score
                best_idx = idx

        if best_idx is not None:
            selected.append(best_idx)
            remaining.remove(best_idx)
        else:
            break

    return [candidates[i] for i in selected]


def rerank_rrf(
    ranked_lists: list[list[dict]], top_k: int = 5, k: int = 60
) -> list[dict]:
    """
    Reciprocal Rank Fusion — gộp kết quả từ nhiều ranker.

    RRF(d) = Σ 1 / (k + rank_r(d))
    """
    scores, items = {}, {}
    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list, 1):
            key = item.get("id") or item["content"]
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank)
            items.setdefault(key, item)
    ordered = sorted(scores, key=lambda key: scores[key], reverse=True)
    return [{**items[key], "score": scores[key]} for key in ordered[:top_k]]


# =============================================================================
# Main rerank interface
# =============================================================================

def rerank(
    query: str,
    candidates: list[dict],
    top_k: int = 5,
    method: str = "rrf",  # "cross_encoder" | "mmr" | "rrf"
) -> list[dict]:
    """
    Unified reranking interface.
    """
    if not candidates or top_k <= 0:
        return []
    if method == "cross_encoder":
        return rerank_cross_encoder(query, candidates, top_k)
    elif method == "mmr":
        try:
            from .task4_chunking_indexing import get_embedding_model
            model = get_embedding_model()
            q_vec = model.encode(query)
            q_emb = q_vec.tolist() if hasattr(q_vec, "tolist") else list(q_vec)
        except Exception:
            q_emb = [1.0] * 384
        return rerank_mmr(q_emb, candidates, top_k=top_k)
    elif method == "rrf":
        return rerank_rrf([candidates], top_k=top_k)
    else:
        raise ValueError(f"Unknown rerank method: {method}")


if __name__ == "__main__":
    # Test with dummy data
    dummy_candidates = [
        {"content": "Tuition fee payment schedule", "score": 0.8, "metadata": {}},
        {"content": "Scholarship eligibility requirements", "score": 0.6, "metadata": {}},
        {"content": "Library study room booking guide", "score": 0.5, "metadata": {}},
    ]
    results = rerank("tuition fee payment", dummy_candidates, top_k=2)
    for r in results:
        print(f"[{r['score']:.3f}] {r['content']}")
