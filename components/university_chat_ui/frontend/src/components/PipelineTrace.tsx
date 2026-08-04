import { motion } from "motion/react";
import {
  Search,
  Type,
  GitMerge,
  Layers,
  ArrowDownUp,
  Sparkles,
  ShieldCheck,
  MessageCircleQuestion,
  type LucideIcon,
} from "lucide-react";
import type { PipelineStep } from "../types";
import { cn } from "../lib/utils";

const ICONS: Record<string, LucideIcon> = {
  query: MessageCircleQuestion,
  semantic: Search,
  lexical: Type,
  fusion: GitMerge,
  pageindex: Layers,
  reorder: ArrowDownUp,
  generation: Sparkles,
  citation: ShieldCheck,
};

/** Nhãn tiếng Việt cho từng trạng thái — kèm chữ để không chỉ phụ thuộc màu. */
const STATUS_TEXT: Record<PipelineStep["status"], string> = {
  idle: "Chưa chạy",
  running: "Đang chạy",
  success: "Hoàn tất",
  fallback: "Fallback",
  skipped: "Bỏ qua",
  error: "Lỗi",
};

const STATUS_STYLE: Record<PipelineStep["status"], string> = {
  idle: "border-edge bg-white/[0.02] text-muted",
  running: "border-cyan-brand/40 bg-cyan-brand/10 text-cyan-brand",
  success: "border-ok/30 bg-ok/[0.08] text-ink",
  fallback: "border-violet-brand/40 bg-violet-brand/10 text-violet-brand",
  skipped: "border-edge bg-white/[0.02] text-muted",
  error: "border-danger/40 bg-danger/10 text-danger",
};

export default function PipelineTrace({
  steps,
  reducedMotion,
}: {
  steps: PipelineStep[];
  reducedMotion: boolean;
}) {
  if (!steps.length) {
    return (
      <p className="px-1 py-3 text-[12px] text-muted">
        Chưa có lượt hỏi nào. Pipeline trace sẽ hiện sau câu hỏi đầu tiên.
      </p>
    );
  }

  return (
    <ol className="space-y-1" aria-label="Các bước của retrieval pipeline">
      {steps.map((step, index) => {
        const Icon = ICONS[step.id] ?? Sparkles;
        const meta = [
          step.count !== null ? `${step.count} docs` : null,
          step.ms !== null ? `${step.ms} ms` : null,
          STATUS_TEXT[step.status],
        ].filter(Boolean);

        return (
          <motion.li
            key={step.id}
            initial={reducedMotion ? false : { opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.22, delay: reducedMotion ? 0 : index * 0.035 }}
            className={cn(
              "flex items-center gap-2.5 rounded-xl border px-2.5 py-1.5",
              STATUS_STYLE[step.status],
            )}
          >
            <Icon
              size={14}
              aria-hidden="true"
              className={cn("shrink-0", step.status === "running" && !reducedMotion && "animate-pulse")}
            />
            <div className="min-w-0 flex-1">
              <div className="truncate text-[12px] font-medium">{step.label}</div>
              {step.note ? (
                <div className="truncate text-[10.5px] text-muted">{step.note}</div>
              ) : null}
            </div>
            <span className="shrink-0 whitespace-nowrap text-[10.5px] text-muted">
              {meta.join(" · ")}
            </span>
          </motion.li>
        );
      })}
    </ol>
  );
}
