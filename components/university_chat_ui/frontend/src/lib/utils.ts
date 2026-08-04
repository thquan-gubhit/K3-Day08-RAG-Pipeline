import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Ghép className có xử lý xung đột utility của Tailwind. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Sinh nonce cho mỗi sự kiện gửi về Python.
 *
 * Bắt buộc: Streamlit trả lại giá trị component ở MỌI lần rerun sau đó, nên nếu
 * không có nonce, Python sẽ xử lý cùng một lần submit lặp vô hạn.
 */
export function createNonce(): string {
  const cryptoObj = globalThis.crypto;
  if (cryptoObj && typeof cryptoObj.randomUUID === "function") {
    return cryptoObj.randomUUID();
  }
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

/** Kiểm tra trình duyệt có hỗ trợ WebGL không (quyết định render Three.js hay fallback CSS). */
export function supportsWebGL(): boolean {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(
      window.WebGLRenderingContext &&
        (canvas.getContext("webgl") || canvas.getContext("experimental-webgl")),
    );
  } catch {
    return false;
  }
}

/** Người dùng có bật "giảm chuyển động" ở cấp hệ điều hành không. */
export function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

/**
 * Chỉ cho phép mở link http/https.
 * Chặn javascript:, data:, file: — nguồn dữ liệu đến từ tài liệu bên ngoài nên
 * không được tin tưởng.
 */
export function safeHref(url: string): string | null {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:" ? parsed.href : null;
  } catch {
    return null;
  }
}

/** Định dạng điểm số theo đúng loại metric — không quy đổi RRF thành phần trăm. */
export function formatScore(score: number | null, metric: string): string {
  if (score === null || Number.isNaN(score)) return "Không có điểm";
  if (metric.toLowerCase().includes("cosine")) {
    // Cosine nằm trong [0,1] nên phần trăm mới có ý nghĩa — luôn kèm nhãn metric.
    return `${(score * 100).toFixed(1)}% · Cosine similarity`;
  }
  return `${score.toFixed(4)} · ${metric}`;
}

/** Tách citation [Nguồn, Năm] khỏi văn bản để highlight riêng. */
export const CITATION_PATTERN = /\[[^[\]\n]{1,160}?,\s*[^[\]\n]{1,40}?\]/g;

/** Rút từ khoá của câu hỏi để highlight trong excerpt. */
export function highlightParts(text: string, terms: string[]): Array<{ text: string; hit: boolean }> {
  if (!terms.length || !text) return [{ text, hit: false }];
  const escaped = terms
    .filter((t) => t.length > 2)
    .map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))
    .sort((a, b) => b.length - a.length);
  if (!escaped.length) return [{ text, hit: false }];

  const pattern = new RegExp(`(${escaped.join("|")})`, "gi");
  return text
    .split(pattern)
    .filter((part) => part !== "")
    .map((part) => ({ text: part, hit: pattern.test(part) && new RegExp(`^(${escaped.join("|")})$`, "i").test(part) }));
}
