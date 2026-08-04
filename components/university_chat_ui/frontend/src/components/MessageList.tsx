import { useEffect, useRef, useState, type ReactNode } from "react";
import { AnimatePresence, motion } from "motion/react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { AlertTriangle, Check, Copy, Library } from "lucide-react";
import type { ChatMessage } from "../types";
import { cn, CITATION_PATTERN } from "../lib/utils";

type Props = {
  messages: ChatMessage[];
  isGenerating: boolean;
  reducedMotion: boolean;
  onShowSources: () => void;
  emptyState: ReactNode;
};

/**
 * Render citation [Nguồn, Năm] nổi bật.
 *
 * Quan trọng: markdown được render với react-markdown và KHÔNG bật rehype-raw,
 * nên HTML thô trong câu trả lời của LLM không bao giờ được thực thi.
 */
function CitationText({ children }: { children: ReactNode }) {
  if (typeof children !== "string") return <>{children}</>;

  const parts = children.split(CITATION_PATTERN);
  const matches = children.match(CITATION_PATTERN) ?? [];
  if (!matches.length) return <>{children}</>;

  const out: ReactNode[] = [];
  parts.forEach((part, i) => {
    out.push(<span key={`t${i}`}>{part}</span>);
    if (matches[i]) {
      out.push(
        <span
          key={`c${i}`}
          className="mx-0.5 rounded border border-cyan-brand/35 bg-cyan-brand/12 px-1 py-px font-mono text-[11.5px] text-cyan-brand"
        >
          <span className="sr-only">Trích dẫn nguồn: </span>
          {matches[i]}
        </span>,
      );
    }
  });
  return <>{out}</>;
}

function CopyButton({ text, reducedMotion }: { text: string; reducedMotion: boolean }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      aria-label="Sao chép câu trả lời"
      onClick={async () => {
        try {
          await navigator.clipboard.writeText(text);
          setCopied(true);
          window.setTimeout(() => setCopied(false), 1600);
        } catch {
          /* clipboard bị chặn trong iframe — bỏ qua */
        }
      }}
      className="chip transition hover:border-cyan-brand/45 hover:text-cyan-brand"
    >
      <AnimatePresence mode="wait" initial={false}>
        {copied ? (
          <motion.span
            key="ok"
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
  );
}

/** Ba chấm nhấp nháy khi đang chờ câu trả lời. */
function TypingIndicator({ reducedMotion }: { reducedMotion: boolean }) {
  return (
    <div
      className="panel inline-flex items-center gap-2 px-3 py-2"
      role="status"
      aria-live="polite"
    >
      <span className="sr-only">Đang tổng hợp câu trả lời</span>
      <div className="flex gap-1" aria-hidden="true">
        {[0, 1, 2].map((i) => (
          <motion.span
            key={i}
            className="h-1.5 w-1.5 rounded-full bg-cyan-brand"
            animate={reducedMotion ? { opacity: 0.7 } : { opacity: [0.25, 1, 0.25] }}
            transition={{ duration: 1.05, repeat: reducedMotion ? 0 : Infinity, delay: i * 0.16 }}
          />
        ))}
      </div>
      <span className="text-[12px] text-muted">Đang truy xuất tài liệu và tổng hợp…</span>
    </div>
  );
}

export default function MessageList({
  messages,
  isGenerating,
  reducedMotion,
  onShowSources,
  emptyState,
}: Props) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "end" });
  }, [messages.length, isGenerating, reducedMotion]);

  if (!messages.length && !isGenerating) {
    return <>{emptyState}</>;
  }

  return (
    <div className="space-y-3">
      {messages.map((message) => {
        const isUser = message.role === "user";
        const meta = [
          message.createdAt,
          message.latencyMs != null ? `${message.latencyMs} ms` : null,
          message.sourceCount ? `${message.sourceCount} nguồn` : null,
          message.citationCount ? `${message.citationCount} citation` : null,
          message.model,
          message.retrievalSource === "pageindex" ? "PageIndex fallback" : null,
        ].filter(Boolean);

        return (
          <motion.div
            key={message.id}
            initial={reducedMotion ? false : { opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.26 }}
            className={cn("flex", isUser ? "justify-end" : "justify-start")}
          >
            <div className={cn("max-w-[92%] sm:max-w-[85%]", isUser && "text-right")}>
              <div
                className={cn(
                  "rounded-2xl px-3.5 py-2.5 text-left",
                  isUser
                    ? "bg-gradient-to-br from-indigo-brand/25 to-cyan-brand/15 border border-indigo-brand/30"
                    : "panel",
                  message.error && "border-danger/40",
                )}
              >
                {isUser ? (
                  <p className="whitespace-pre-wrap text-[13.5px] leading-relaxed text-ink">
                    {message.content}
                  </p>
                ) : (
                  <div className="markdown-body">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        p: ({ children }) => (
                          <p>
                            <CitationText>{children as ReactNode}</CitationText>
                          </p>
                        ),
                        li: ({ children }) => (
                          <li>
                            <CitationText>{children as ReactNode}</CitationText>
                          </li>
                        ),
                        a: ({ href, children }) => {
                          // Chỉ cho phép http/https trong link do LLM sinh ra.
                          const ok = href && /^https?:\/\//i.test(href);
                          return ok ? (
                            <a href={href} target="_blank" rel="noopener noreferrer">
                              {children}
                            </a>
                          ) : (
                            <span>{children}</span>
                          );
                        },
                      }}
                    >
                      {message.content}
                    </ReactMarkdown>
                  </div>
                )}
              </div>

              {message.unknownCitations.length > 0 ? (
                <p className="mt-1 flex items-center gap-1 text-[11px] text-warn">
                  <AlertTriangle size={11} aria-hidden="true" />
                  Có citation không khớp nguồn: {message.unknownCitations.slice(0, 2).join(", ")}
                </p>
              ) : null}

              <div
                className={cn(
                  "mt-1 flex flex-wrap items-center gap-1.5",
                  isUser ? "justify-end" : "justify-start",
                )}
              >
                <span className="text-[10.5px] text-muted">{meta.join(" · ")}</span>
                {!isUser ? (
                  <>
                    <CopyButton text={message.content} reducedMotion={reducedMotion} />
                    {message.sourceCount ? (
                      <button
                        type="button"
                        onClick={onShowSources}
                        aria-label="Xem các nguồn đã dùng cho câu trả lời này"
                        className="chip transition hover:border-cyan-brand/45 hover:text-cyan-brand"
                      >
                        <Library size={11} aria-hidden="true" /> Xem nguồn
                      </button>
                    ) : null}
                  </>
                ) : null}
              </div>
            </div>
          </motion.div>
        );
      })}

      <AnimatePresence>
        {isGenerating ? (
          <motion.div
            initial={reducedMotion ? false : { opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
          >
            <TypingIndicator reducedMotion={reducedMotion} />
          </motion.div>
        ) : null}
      </AnimatePresence>

      <div ref={endRef} />
    </div>
  );
}
