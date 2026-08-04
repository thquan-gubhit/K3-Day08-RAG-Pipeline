/**
 * Hằng số chủ đề + fallback SVG cho KnowledgeOrb.
 *
 * File này CỐ Ý không import three.js: App.tsx và EmptyState.tsx cần `TOPICS`
 * và `KnowledgeOrbFallback` ngay lần render đầu, nếu import chung với scene 3D
 * thì bundle three.js sẽ bị kéo vào chunk chính và mất tác dụng lazy-load.
 */

/** 6 chủ đề dịch vụ đại học — mỗi node trong knowledge graph là một topic. */
export const TOPICS = [
  { label: "Học phí", color: "#22D3EE" },
  { label: "Học bổng", color: "#6366F1" },
  { label: "Ký túc xá", color: "#A78BFA" },
  { label: "Đăng ký học phần", color: "#34D399" },
  { label: "Thư viện", color: "#FBBF24" },
  { label: "Hỗ trợ sinh viên", color: "#FB7185" },
] as const;

/** Fallback CSS/SVG thuần khi WebGL không khả dụng hoặc scene chưa nạp xong. */
export function KnowledgeOrbFallback({ className }: { className?: string }) {
  return (
    <div
      className={className}
      role="img"
      aria-label="Sơ đồ tri thức: lõi trung tâm và sáu node chủ đề dịch vụ đại học"
    >
      <svg viewBox="0 0 200 200" className="h-full w-full">
        <defs>
          <radialGradient id="orbCore">
            <stop offset="0%" stopColor="#22D3EE" stopOpacity="0.95" />
            <stop offset="55%" stopColor="#6366F1" stopOpacity="0.45" />
            <stop offset="100%" stopColor="#07111F" stopOpacity="0" />
          </radialGradient>
        </defs>
        <circle cx="100" cy="100" r="60" fill="url(#orbCore)" />
        <circle cx="100" cy="100" r="74" fill="none" stroke="#6366F1" strokeOpacity="0.28" />
        {TOPICS.map((topic, i) => {
          const angle = (i / TOPICS.length) * Math.PI * 2;
          const x = 100 + Math.cos(angle) * 74;
          const y = 100 + Math.sin(angle) * 74;
          return (
            <g key={topic.label}>
              <line x1="100" y1="100" x2={x} y2={y} stroke={topic.color} strokeOpacity="0.3" />
              <circle cx={x} cy={y} r="5" fill={topic.color} fillOpacity="0.85" />
            </g>
          );
        })}
      </svg>
    </div>
  );
}
