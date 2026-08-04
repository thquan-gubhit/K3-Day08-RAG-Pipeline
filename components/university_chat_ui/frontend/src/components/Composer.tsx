import { useRef, useState, type KeyboardEvent } from "react";
import { motion } from "motion/react";
import { Loader2, SendHorizontal } from "lucide-react";
import { cn } from "../lib/utils";

const MAX_CHARS = 500;

type Props = {
  disabled: boolean;
  reducedMotion: boolean;
  onSubmit: (query: string) => void;
};

/**
 * Ô nhập câu hỏi.
 *
 * - Enter gửi, Shift+Enter xuống dòng.
 * - Chặn gửi chuỗi rỗng và chặn double-submit (cờ `sending` + `disabled`).
 * - Giới hạn 500 ký tự, hiển thị số ký tự còn lại.
 */
export default function Composer({ disabled, reducedMotion, onSubmit }: Props) {
  const [value, setValue] = useState("");
  const sending = useRef(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const submit = () => {
    const query = value.trim();
    // Chặn gửi trùng: một lần nhấn Enter + click nút không được tạo 2 request.
    if (!query || disabled || sending.current) return;
    sending.current = true;
    onSubmit(query);
    setValue("");
    // Streamlit sẽ rerun và render lại component; mở khoá sau một nhịp ngắn
    // để phòng trường hợp rerun bị chậm.
    window.setTimeout(() => {
      sending.current = false;
    }, 600);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  const remaining = MAX_CHARS - value.length;

  return (
    <div className="panel p-2">
      <div className="flex items-end gap-2">
        <label htmlFor="rag-composer" className="sr-only">
          Nhập câu hỏi về dịch vụ đại học
        </label>
        <textarea
          id="rag-composer"
          ref={textareaRef}
          rows={1}
          value={value}
          maxLength={MAX_CHARS}
          disabled={disabled}
          onChange={(e) => setValue(e.target.value.slice(0, MAX_CHARS))}
          onKeyDown={handleKeyDown}
          placeholder="Hỏi về học phí, học bổng, ký túc xá, đăng ký học phần…"
          aria-describedby="rag-composer-help"
          className={cn(
            "max-h-28 min-h-[38px] flex-1 resize-none rounded-xl bg-transparent px-2.5 py-2",
            "text-[13.5px] text-ink placeholder:text-muted/70 focus:outline-none",
            disabled && "cursor-not-allowed opacity-60",
          )}
        />
        <motion.button
          type="button"
          onClick={submit}
          disabled={disabled || !value.trim()}
          aria-label={disabled ? "Đang xử lý câu hỏi" : "Gửi câu hỏi"}
          whileTap={reducedMotion || disabled ? undefined : { scale: 0.93 }}
          className={cn(
            "grid h-9 w-9 shrink-0 place-items-center rounded-xl transition",
            "bg-gradient-to-br from-cyan-brand to-indigo-brand text-[#04121f]",
            "disabled:cursor-not-allowed disabled:opacity-40",
          )}
        >
          {disabled ? (
            <Loader2 size={16} className={cn(!reducedMotion && "animate-spin")} aria-hidden="true" />
          ) : (
            <SendHorizontal size={16} aria-hidden="true" />
          )}
        </motion.button>
      </div>
      <div
        id="rag-composer-help"
        className="flex items-center justify-between px-2.5 pb-0.5 pt-1 text-[10.5px] text-muted"
      >
        <span>Enter để gửi · Shift+Enter để xuống dòng</span>
        <span className={cn(remaining < 50 && "text-warn")}>còn {remaining} ký tự</span>
      </div>
    </div>
  );
}
