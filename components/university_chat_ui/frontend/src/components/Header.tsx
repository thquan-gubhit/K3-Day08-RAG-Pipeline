import { motion } from "motion/react";
import { GraduationCap, Plus, AlertTriangle, CheckCircle2 } from "lucide-react";
import type { StatusItem, SystemStatus } from "../types";
import { cn } from "../lib/utils";

type Props = {
  status: SystemStatus;
  onNewConversation: () => void;
  reducedMotion: boolean;
};

/** Badge trạng thái — luôn có icon + chữ, không chỉ dựa vào màu (accessibility). */
function StatusBadge({ item }: { item: StatusItem }) {
  const Icon = item.ok ? CheckCircle2 : AlertTriangle;
  return (
    <span
      className={cn(
        "chip",
        item.ok ? "border-ok/40 text-ok" : "border-warn/40 text-warn",
      )}
      title={item.detail}
    >
      <Icon size={11} aria-hidden="true" />
      {item.label}
      <span className="sr-only">: {item.ok ? "sẵn sàng" : "cảnh báo"} — {item.detail}</span>
    </span>
  );
}

export default function Header({ status, onNewConversation, reducedMotion }: Props) {
  const badges: StatusItem[] = [
    status.chroma,
    status.bm25,
    status.rrf,
    status.pageindex,
    status.api,
  ];

  return (
    <header
      className={cn(
        "panel relative overflow-hidden px-5 py-4",
        "bg-[linear-gradient(120deg,rgba(34,211,238,.16),rgba(99,102,241,.16)_46%,rgba(167,139,250,.16))]",
        "bg-[length:220%_100%]",
        !reducedMotion && "animate-drift",
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          <motion.div
            initial={reducedMotion ? false : { scale: 0.85, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ duration: 0.35 }}
            className="grid h-10 w-10 shrink-0 place-items-center rounded-xl bg-gradient-to-br from-cyan-brand to-indigo-brand text-base"
            aria-hidden="true"
          >
            <GraduationCap size={20} className="text-[#04121f]" />
          </motion.div>
          <div className="min-w-0">
            <h1 className="truncate text-[15px] font-semibold tracking-tight text-ink">
              University Services RAG Assistant
            </h1>
            <p className="truncate text-[12px] text-muted">Hybrid Retrieval • Citation-grounded</p>
          </div>
        </div>

        <button
          type="button"
          onClick={onNewConversation}
          aria-label="Bắt đầu cuộc trò chuyện mới"
          className="chip shrink-0 border-cyan-brand/40 text-cyan-brand transition hover:bg-cyan-brand/10"
        >
          <Plus size={12} aria-hidden="true" />
          Cuộc trò chuyện mới
        </button>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        <span
          className={cn("chip", status.corpus.ok ? "border-ok/40 text-ok" : "border-warn/40 text-warn")}
        >
          {status.corpus.ok ? "Pipeline sẵn sàng" : "Thiếu dữ liệu corpus"}
        </span>
        {badges.map((item) => (
          <StatusBadge key={item.label} item={item} />
        ))}
      </div>
    </header>
  );
}
