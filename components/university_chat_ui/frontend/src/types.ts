import { z } from "zod";

/**
 * Hợp đồng dữ liệu giữa Streamlit (Python) và React.
 *
 * Mọi props đi vào đều được zod validate trước khi render: Streamlit gửi JSON
 * thuần, và nếu phía Python đổi schema mà quên cập nhật frontend thì ta muốn
 * thấy fallback an toàn thay vì crash cả iframe.
 */

export const ChatMessageSchema = z.object({
  id: z.string(),
  role: z.enum(["user", "assistant"]),
  content: z.string(),
  createdAt: z.string().default(""),
  latencyMs: z.number().nullable().optional(),
  sourceCount: z.number().default(0),
  citationCount: z.number().default(0),
  unknownCitations: z.array(z.string()).default([]),
  retrievalSource: z.string().nullable().optional(),
  model: z.string().nullable().optional(),
  error: z.string().nullable().optional(),
});

export const SourceDocumentSchema = z.object({
  id: z.string(),
  rank: z.number(),
  name: z.string(),
  title: z.string().default(""),
  file_name: z.string().default(""),
  doc_type: z.string().default(""),
  retrieval_type: z.string().default(""),
  origin: z.string().default("hybrid"),
  score: z.number().nullable(),
  score_metric: z.string().default(""),
  year: z.string().default("n.d."),
  date: z.string().default(""),
  url: z.string().default(""),
  chunk_id: z.string().default(""),
  citation: z.string().default(""),
  excerpt: z.string().default(""),
  char_count: z.number().default(0),
});

export const PipelineStepSchema = z.object({
  id: z.string(),
  label: z.string(),
  status: z.enum(["idle", "running", "success", "fallback", "skipped", "error"]),
  ms: z.number().nullable(),
  count: z.number().nullable(),
  note: z.string().default(""),
});

export const UISettingsSchema = z.object({
  topK: z.number().min(3).max(10).default(5),
  showScores: z.boolean().default(true),
  showTrace: z.boolean().default(true),
  reducedMotion: z.boolean().default(false),
});

export const StatusItemSchema = z.object({
  ok: z.boolean(),
  label: z.string(),
  detail: z.string(),
});

export const SystemStatusSchema = z.object({
  api: StatusItemSchema,
  chroma: StatusItemSchema,
  bm25: StatusItemSchema,
  rrf: StatusItemSchema,
  pageindex: StatusItemSchema,
  corpus: StatusItemSchema,
  frontend: StatusItemSchema,
  score_threshold: z.number().default(0),
});

export const ChatUIPropsSchema = z.object({
  messages: z.array(ChatMessageSchema).default([]),
  sources: z.array(SourceDocumentSchema).default([]),
  pipelineTrace: z.array(PipelineStepSchema).default([]),
  settings: UISettingsSchema,
  status: SystemStatusSchema,
  suggestedQuestions: z.array(z.string()).default([]),
  isGenerating: z.boolean().default(false),
  selectedSourceId: z.string().nullable().optional(),
  height: z.number().default(720),
});

export type ChatMessage = z.infer<typeof ChatMessageSchema>;
export type SourceDocument = z.infer<typeof SourceDocumentSchema>;
export type PipelineStep = z.infer<typeof PipelineStepSchema>;
export type UISettings = z.infer<typeof UISettingsSchema>;
export type SystemStatus = z.infer<typeof SystemStatusSchema>;
export type StatusItem = z.infer<typeof StatusItemSchema>;
export type ChatUIProps = z.infer<typeof ChatUIPropsSchema>;

/** Sự kiện React gửi ngược về Python. */
export type ChatUIEvent =
  | { type: "submit_query"; query: string }
  | { type: "select_suggestion"; query: string }
  | { type: "new_conversation" }
  | { type: "clear_history" }
  | { type: "update_settings"; payload: Partial<UISettings> }
  | { type: "select_source"; sourceId: string }
  | { type: "export_conversation"; format: "md" | "json" };

/** Giá trị thực sự gửi qua Streamlit — kèm nonce để Python chống xử lý trùng. */
export type ChatUIEventEnvelope = ChatUIEvent & { nonce: string };
