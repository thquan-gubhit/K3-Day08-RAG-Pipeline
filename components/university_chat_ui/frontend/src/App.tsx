import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Streamlit, type ComponentProps } from "streamlit-component-lib";
import { AnimatePresence, motion } from "motion/react";
import { PanelRightClose, PanelRightOpen } from "lucide-react";

import Header from "./components/Header";
import MessageList from "./components/MessageList";
import Composer from "./components/Composer";
import SourceInspector from "./components/SourceInspector";
import PipelineTrace from "./components/PipelineTrace";
import SettingsBar from "./components/SettingsBar";
import SuggestionGrid from "./components/SuggestionGrid";
import EmptyState, { OrbStage } from "./components/EmptyState";
import { TOPICS } from "./three/topics";

import { ChatUIPropsSchema, type ChatUIEvent, type ChatUIProps, type UISettings } from "./types";
import { cn, createNonce, prefersReducedMotion } from "./lib/utils";

/** Fallback dùng khi Python gửi props sai schema — không bao giờ để iframe trắng. */
const SAFE_STATUS_ITEM = { ok: false, label: "—", detail: "Không có dữ liệu" };
const FALLBACK_PROPS: ChatUIProps = {
  messages: [],
  sources: [],
  pipelineTrace: [],
  settings: { topK: 5, showScores: true, showTrace: true, reducedMotion: false },
  status: {
    api: SAFE_STATUS_ITEM,
    chroma: SAFE_STATUS_ITEM,
    bm25: SAFE_STATUS_ITEM,
    rrf: SAFE_STATUS_ITEM,
    pageindex: SAFE_STATUS_ITEM,
    corpus: SAFE_STATUS_ITEM,
    frontend: SAFE_STATUS_ITEM,
    score_threshold: 0,
  },
  suggestedQuestions: [],
  isGenerating: false,
  selectedSourceId: null,
  height: 720,
};

/** Rút từ khoá của câu hỏi gần nhất để highlight trong source excerpt. */
const STOPWORDS = new Set([
  "là", "và", "của", "cho", "các", "những", "một", "có", "được", "trong", "với",
  "thì", "này", "đó", "nào", "gì", "như", "thế", "để", "khi", "tại", "về",
  "the", "a", "an", "of", "for", "and", "to", "in", "on", "is", "are", "what", "how",
]);

function extractTerms(text: string): string[] {
  const seen = new Set<string>();
  for (const raw of text.toLowerCase().match(/[\p{L}\p{N}]+/gu) ?? []) {
    if (raw.length < 3 || STOPWORDS.has(raw)) continue;
    seen.add(raw);
    if (seen.size >= 12) break;
  }
  return [...seen];
}

export default function App({ args, disabled }: ComponentProps) {
  // ---- Validate props từ Python ------------------------------------------
  const parsed = useMemo(() => {
    const result = ChatUIPropsSchema.safeParse(args);
    if (!result.success) {
      // Không crash iframe — log để dev thấy và dùng fallback an toàn.
      console.warn("[university_chat_ui] props không hợp lệ:", result.error.issues);
      return FALLBACK_PROPS;
    }
    return result.data;
  }, [args]);

  const {
    messages,
    sources,
    pipelineTrace,
    settings,
    status,
    suggestedQuestions,
    isGenerating,
    selectedSourceId,
  } = parsed;

  // Reduced motion = người dùng bật trong settings HOẶC cấu hình ở hệ điều hành.
  const systemReducedMotion = useMemo(() => prefersReducedMotion(), []);
  const reducedMotion = settings.reducedMotion || systemReducedMotion;

  const [evidenceOpen, setEvidenceOpen] = useState(true);
  const rootRef = useRef<HTMLDivElement>(null);

  // ---- Gửi sự kiện về Python ---------------------------------------------
  // Mỗi sự kiện kèm nonce mới; Python bỏ qua nonce đã xử lý nên không có
  // vòng lặp rerun vô hạn khi component chỉ re-render.
  const emit = useCallback(
    (event: ChatUIEvent) => {
      if (disabled) return;
      Streamlit.setComponentValue({ ...event, nonce: createNonce() });
    },
    [disabled],
  );

  // ---- Chiều cao iframe ---------------------------------------------------
  useEffect(() => {
    const update = () => {
      const measured = rootRef.current?.scrollHeight ?? 0;
      Streamlit.setFrameHeight(Math.max(measured + 8, 560));
    };
    update();
    const observer = new ResizeObserver(update);
    if (rootRef.current) observer.observe(rootRef.current);
    return () => observer.disconnect();
  }, [messages.length, sources.length, evidenceOpen, pipelineTrace.length, isGenerating]);

  // ---- Dữ liệu dẫn xuất ---------------------------------------------------
  const lastUserQuestion = useMemo(() => {
    for (let i = messages.length - 1; i >= 0; i -= 1) {
      if (messages[i].role === "user") return messages[i].content;
    }
    return "";
  }, [messages]);

  const terms = useMemo(() => extractTerms(lastUserQuestion), [lastUserQuestion]);

  // Node 3D nào được highlight khi chọn một source: khớp theo chủ đề trong tên file.
  const highlightIndex = useMemo(() => {
    if (!selectedSourceId) return null;
    const source = sources.find((s) => s.id === selectedSourceId);
    if (!source) return null;
    const haystack = `${source.name} ${source.file_name} ${source.title}`.toLowerCase();
    const keywords = ["fee", "scholarship", "accommodation", "enrol", "librar", "support"];
    const found = keywords.findIndex((k) => haystack.includes(k));
    return found >= 0 && found < TOPICS.length ? found : null;
  }, [selectedSourceId, sources]);

  const usedPageIndex = sources.some((s) => s.origin === "pageindex");
  const hasConversation = messages.length > 0;

  const updateSettings = (patch: Partial<UISettings>) =>
    emit({ type: "update_settings", payload: patch });

  return (
    <div
      ref={rootRef}
      className="min-h-[540px] w-full space-y-3 bg-transparent p-0.5 text-ink"
    >
      <Header
        status={status}
        reducedMotion={reducedMotion}
        onNewConversation={() => emit({ type: "new_conversation" })}
      />

      {/*
        Breakpoint tính theo bề rộng của CHÍNH iframe component (Streamlit giới
        hạn container ~1100px), nên dùng lg (1024px) cho bố cục 3 vùng thay vì
        xl — nếu để xl thì ở màn hình 1280px vẫn không bao giờ đạt 3 cột.

        Desktop (lg): 3 vùng (điều hướng | chat | evidence) — chat rộng nhất.
        Tablet (md): 2 cột. Mobile: 1 cột, evidence xuống dưới dạng accordion.
      */}
      <div
        className={cn(
          "grid gap-3",
          "grid-cols-1",
          "md:grid-cols-[210px_minmax(0,1fr)]",
          evidenceOpen
            ? "lg:grid-cols-[200px_minmax(0,1fr)_310px]"
            : "lg:grid-cols-[200px_minmax(0,1fr)_44px]",
        )}
      >
        {/* ---------- Cột trái: gợi ý + thiết lập ---------- */}
        <aside className="order-2 space-y-3 md:order-1">
          <SuggestionGrid
            questions={suggestedQuestions}
            disabled={isGenerating || disabled}
            reducedMotion={reducedMotion}
            onSelect={(question) => emit({ type: "select_suggestion", query: question })}
          />
          <SettingsBar
            settings={settings}
            scoreThreshold={status.score_threshold}
            onChange={updateSettings}
            onClearHistory={() => emit({ type: "clear_history" })}
          />
        </aside>

        {/* ---------- Cột giữa: chat workspace ---------- */}
        <main className="order-1 flex min-w-0 flex-col gap-3 md:order-2">
          {hasConversation ? (
            <div className="panel overflow-hidden px-2 pb-1 pt-2">
              <OrbStage
                active={isGenerating}
                reducedMotion={reducedMotion}
                highlightIndex={highlightIndex}
                compact
              />
            </div>
          ) : null}

          <div className="scroll-area max-h-[52vh] min-h-[220px] overflow-y-auto pr-1">
            <MessageList
              messages={messages}
              isGenerating={isGenerating}
              reducedMotion={reducedMotion}
              onShowSources={() => setEvidenceOpen(true)}
              emptyState={
                <EmptyState
                  active={isGenerating}
                  reducedMotion={reducedMotion}
                  highlightIndex={highlightIndex}
                />
              }
            />
          </div>

          <Composer
            disabled={isGenerating || disabled}
            reducedMotion={reducedMotion}
            onSubmit={(query) => emit({ type: "submit_query", query })}
          />
        </main>

        {/* ---------- Cột phải: evidence panel (collapse được) ---------- */}
        <aside className="order-3 min-w-0">
          <div className="panel p-2.5">
            <div className="flex items-center justify-between gap-2">
              <h2 className="text-[10.5px] uppercase tracking-[0.1em] text-muted">
                Evidence panel
              </h2>
              <button
                type="button"
                onClick={() => setEvidenceOpen((v) => !v)}
                aria-expanded={evidenceOpen}
                aria-controls="rag-evidence-body"
                aria-label={evidenceOpen ? "Thu gọn bảng nguồn" : "Mở bảng nguồn"}
                className="rounded-lg p-1 text-muted transition hover:text-cyan-brand"
              >
                {evidenceOpen ? <PanelRightClose size={14} /> : <PanelRightOpen size={14} />}
              </button>
            </div>

            <AnimatePresence initial={false}>
              {evidenceOpen ? (
                <motion.div
                  id="rag-evidence-body"
                  key="evidence"
                  initial={reducedMotion ? false : { opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={reducedMotion ? { opacity: 0 } : { opacity: 0, height: 0 }}
                  transition={{ duration: 0.24 }}
                  className="overflow-hidden"
                >
                  {usedPageIndex ? (
                    <p className="mt-2 rounded-lg border border-violet-brand/40 bg-violet-brand/10 px-2 py-1.5 text-[11px] text-violet-brand">
                      Pipeline đã chuyển sang <strong>PageIndex vectorless fallback</strong> vì điểm
                      cosine thấp hơn ngưỡng {status.score_threshold.toFixed(2)}.
                    </p>
                  ) : null}

                  <div className="scroll-area mt-2 max-h-[320px] space-y-2 overflow-y-auto pr-1">
                    <SourceInspector
                      sources={sources}
                      terms={terms}
                      selectedSourceId={selectedSourceId ?? null}
                      showScores={settings.showScores}
                      reducedMotion={reducedMotion}
                      isGenerating={isGenerating}
                      onSelect={(sourceId) => emit({ type: "select_source", sourceId })}
                    />
                  </div>

                  {settings.showTrace ? (
                    <div className="mt-3 border-t border-edge pt-2.5">
                      <h3 className="mb-1.5 text-[10.5px] uppercase tracking-[0.1em] text-muted">
                        Pipeline trace
                      </h3>
                      <PipelineTrace steps={pipelineTrace} reducedMotion={reducedMotion} />
                    </div>
                  ) : null}
                </motion.div>
              ) : null}
            </AnimatePresence>
          </div>
        </aside>
      </div>
    </div>
  );
}
