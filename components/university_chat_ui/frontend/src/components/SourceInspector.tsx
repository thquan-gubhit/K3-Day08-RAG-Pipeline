import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Check, ChevronDown, Copy, ExternalLink, FileText } from "lucide-react";
import type { SourceDocument } from "../types";
import { cn, formatScore, highlightParts, safeHref } from "../lib/utils";

type Props = {
  sources: SourceDocument[];
  /** Từ khoá của câu hỏi để highlight trong excerpt. */
  terms: string[];
  selectedSourceId: string | null;
  showScores: boolean;
  reducedMotion: boolean;
  onSelect: (sourceId: string) => void;
};

/** Màu chip theo loại retrieval — kèm text nên không phụ thuộc riêng vào màu. */
const ORIGIN_STYLE: Record<string, string> = {
  hybrid: "border-indigo-brand/45 text-indigo-brand",
  pageindex: "border-violet-brand/45 text-violet-brand",
  semantic: "border-cyan-brand/45 text-cyan-brand",
  bm25: "border-warn/45 text-warn",
};

function SourceCard({
  source,
  terms,
  selected,
  showScores,
  reducedMotion,
  onSelect,
}: {
  source: SourceDocument;
  terms: string[];
  selected: boolean;
  showScores: boolean;
  reducedMotion: boolean;
  onSelect: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [copied, setCopied] = useState(false);
  const href = safeHref(source.url);
  const originKey = (source.origin || "hybrid").toLowerCase();

  const copyExcerpt = async () => {
    try {
      await navigator.clipboard.writeText(source.excerpt);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      // Clipboard bị chặn trong iframe — bỏ qua, không làm hỏng UI.
    }
  };

  return (
    <motion.article
      layout={!reducedMotion}
      onClick={onSelect}
      className={cn(
        "panel cursor-pointer p-3 transition",
        "hover:border-cyan-brand/35 hover:shadow-[0_6px_20px_-12px_rgba(34,211,238,.5)]",
        selected && "border-cyan-brand/55 bg-cyan-brand/[0.06]",
      )}
      aria-label={`Nguồn số ${source.rank}: ${source.title || source.name}`}
    >
      <div className="flex items-start gap-2">
        <span className="shrink-0 rounded-md bg-gradient-to-br from-cyan-brand to-indigo-brand px-1.5 py-0.5 text-[11px] font-bold text-[#04121f]">
          #{source.rank}
        </span>
        <div className="min-w-0 flex-1">
          <p className="break-words text-[12.5px] font-semibold leading-snug text-ink">
            {source.title || source.name}
          </p>
          {source.file_name && source.file_name !== source.name ? (
            <p className="mt-0.5 flex items-center gap-1 truncate text-[10.5px] text-muted">
              <FileText size={10} aria-hidden="true" />
              {source.file_name}
            </p>
          ) : null}
        </div>
      </div>

      <div className="mt-2 flex flex-wrap gap-1">
        <span className={cn("chip", ORIGIN_STYLE[originKey] ?? "")}>
          {source.retrieval_type || source.origin}
        </span>
        {source.doc_type ? <span className="chip">{source.doc_type}</span> : null}
        <span className="chip">{source.year}</span>
      </div>

      {showScores ? (
        <p className="mt-2 text-[11px] text-muted">
          <span className="text-ink">Điểm:</span> {formatScore(source.score, source.score_metric)}
        </p>
      ) : null}

      {source.chunk_id ? (
        <p className="mt-0.5 truncate font-mono text-[10px] text-muted" title={source.chunk_id}>
          {source.chunk_id}
        </p>
      ) : null}

      <p className="mt-2 text-[11.5px] leading-relaxed text-muted">
        {highlightParts(expanded ? source.excerpt : source.excerpt.slice(0, 190), terms).map(
          (part, i) =>
            part.hit ? (
              <mark key={i} className="rounded bg-cyan-brand/25 px-0.5 text-ink">
                {part.text}
              </mark>
            ) : (
              <span key={i}>{part.text}</span>
            ),
        )}
        {!expanded && source.excerpt.length > 190 ? "…" : null}
      </p>

      <div className="mt-2 flex flex-wrap items-center gap-1.5">
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            setExpanded((v) => !v);
          }}
          aria-expanded={expanded}
          aria-label={expanded ? "Thu gọn trích đoạn" : "Mở rộng trích đoạn"}
          className="chip transition hover:border-cyan-brand/45 hover:text-cyan-brand"
        >
          <ChevronDown
            size={11}
            aria-hidden="true"
            className={cn("transition-transform", expanded && "rotate-180")}
          />
          {expanded ? "Thu gọn" : "Mở rộng"}
        </button>

        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            void copyExcerpt();
          }}
          aria-label="Sao chép trích đoạn"
          className="chip transition hover:border-cyan-brand/45 hover:text-cyan-brand"
        >
          <AnimatePresence mode="wait" initial={false}>
            {copied ? (
              <motion.span
                key="done"
                initial={reducedMotion ? false : { scale: 0.6, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.6, opacity: 0 }}
                className="flex items-center gap-1 text-ok"
              >
                <Check size={11} aria-hidden="true" /> Đã chép
              </motion.span>
            ) : (
              <motion.span key="idle" className="flex items-center gap-1">
                <Copy size={11} aria-hidden="true" /> Chép
              </motion.span>
            )}
          </AnimatePresence>
        </button>

        {href ? (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            aria-label="Mở nguồn gốc trong tab mới"
            className="chip transition hover:border-cyan-brand/45 hover:text-cyan-brand"
          >
            <ExternalLink size={11} aria-hidden="true" /> Mở nguồn
          </a>
        ) : null}
      </div>
    </motion.article>
  );
}

/** Skeleton hiển thị trong lúc pipeline đang chạy. */
function SourceSkeleton() {
  return (
    <div className="panel space-y-2 p-3" aria-hidden="true">
      <div className="h-3 w-2/3 animate-pulse rounded bg-white/10" />
      <div className="h-2 w-1/3 animate-pulse rounded bg-white/[0.07]" />
      <div className="h-2 w-full animate-pulse rounded bg-white/[0.07]" />
      <div className="h-2 w-4/5 animate-pulse rounded bg-white/[0.07]" />
    </div>
  );
}

export default function SourceInspector({
  sources,
  terms,
  selectedSourceId,
  showScores,
  reducedMotion,
  onSelect,
  isGenerating,
}: Props & { isGenerating: boolean }) {
  if (isGenerating && !sources.length) {
    return (
      <div className="space-y-2" role="status" aria-live="polite">
        <span className="sr-only">Đang truy xuất nguồn tài liệu</span>
        <SourceSkeleton />
        <SourceSkeleton />
      </div>
    );
  }

  if (!sources.length) {
    return (
      <p className="px-1 py-3 text-[12px] text-muted">
        Chưa có nguồn nào. Hãy đặt một câu hỏi để xem tài liệu hệ thống đã dùng.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {sources.map((source, index) => (
        <motion.div
          key={source.id}
          initial={reducedMotion ? false : { opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.24, delay: reducedMotion ? 0 : index * 0.05 }}
        >
          <SourceCard
            source={source}
            terms={terms}
            selected={selectedSourceId === source.id}
            showScores={showScores}
            reducedMotion={reducedMotion}
            onSelect={() => onSelect(source.id)}
          />
        </motion.div>
      ))}
    </div>
  );
}
