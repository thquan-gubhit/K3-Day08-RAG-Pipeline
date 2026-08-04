import { Suspense, lazy, useEffect, useMemo, useState } from "react";
import { motion } from "motion/react";
import { supportsWebGL } from "../lib/utils";
import { KnowledgeOrbFallback } from "../three/topics";

// Lazy-load scene 3D: chunk three.js không chặn lần render đầu của khung chat.
const KnowledgeOrb = lazy(() => import("../three/KnowledgeOrb"));

type Props = {
  active: boolean;
  reducedMotion: boolean;
  highlightIndex: number | null;
  /** Chiều cao scene: lớn ở empty state, nhỏ khi đã có hội thoại. */
  compact?: boolean;
};

/**
 * Khu vực visual 3D.
 *
 * - Empty state: cao ~300px, là điểm nhấn của màn hình.
 * - Khi đã có hội thoại: `compact` → thu nhỏ, không chiếm chỗ của nội dung.
 * - Không có WebGL → fallback SVG thuần.
 */
export function OrbStage({ active, reducedMotion, highlightIndex, compact = false }: Props) {
  const webgl = useMemo(() => supportsWebGL(), []);
  // Chỉ mount scene sau khi khung chat đã hiện — tránh tranh chấp main thread.
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    const id = window.setTimeout(() => setMounted(true), 120);
    return () => window.clearTimeout(id);
  }, []);

  const height = compact ? "h-[92px]" : "h-[300px] sm:h-[320px]";

  if (!webgl) {
    return <KnowledgeOrbFallback className={`${height} w-full opacity-80`} />;
  }

  return (
    <div className={`${height} w-full`} aria-hidden="true">
      {mounted ? (
        <Suspense fallback={<KnowledgeOrbFallback className="h-full w-full opacity-60" />}>
          <KnowledgeOrb
            active={active}
            highlightIndex={highlightIndex}
            reducedMotion={reducedMotion}
          />
        </Suspense>
      ) : (
        <KnowledgeOrbFallback className="h-full w-full opacity-50" />
      )}
    </div>
  );
}

export default function EmptyState({ active, reducedMotion, highlightIndex }: Props) {
  return (
    <motion.div
      initial={reducedMotion ? false : { opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="panel flex flex-col items-center px-5 py-6 text-center"
    >
      <OrbStage active={active} reducedMotion={reducedMotion} highlightIndex={highlightIndex} />
      <h2 className="mt-2 text-[15px] font-semibold text-ink">
        Bắt đầu bằng một câu hỏi về dịch vụ đại học
      </h2>
      <p className="mt-1.5 max-w-lg text-[12.5px] leading-relaxed text-muted">
        Hệ thống tìm kiếm song song bằng ChromaDB (ngữ nghĩa) và BM25 (từ khoá), hợp nhất bằng RRF,
        và chỉ trả lời dựa trên tài liệu tìm được — mọi khẳng định đều kèm trích dẫn nguồn.
      </p>
    </motion.div>
  );
}
