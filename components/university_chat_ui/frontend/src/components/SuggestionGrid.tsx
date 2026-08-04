import { motion } from "motion/react";
import { MessageSquarePlus } from "lucide-react";

type Props = {
  questions: string[];
  disabled: boolean;
  reducedMotion: boolean;
  onSelect: (question: string) => void;
};

/** Danh sách câu hỏi gợi ý — click là gửi thẳng vào pipeline. */
export default function SuggestionGrid({ questions, disabled, reducedMotion, onSelect }: Props) {
  if (!questions.length) return null;

  return (
    <div className="space-y-1.5">
      <p className="px-1 text-[10.5px] uppercase tracking-[0.1em] text-muted">Câu hỏi gợi ý</p>
      <ul className="space-y-1.5">
        {questions.map((question, index) => (
          <motion.li
            key={question}
            initial={reducedMotion ? false : { opacity: 0, x: -6 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.22, delay: reducedMotion ? 0 : index * 0.04 }}
          >
            <button
              type="button"
              disabled={disabled}
              onClick={() => onSelect(question)}
              className="panel flex w-full items-start gap-2 px-2.5 py-2 text-left text-[12px] leading-snug text-muted transition hover:border-cyan-brand/35 hover:text-ink disabled:cursor-not-allowed disabled:opacity-50"
            >
              <MessageSquarePlus size={13} className="mt-px shrink-0 text-cyan-brand" aria-hidden="true" />
              <span>{question}</span>
            </button>
          </motion.li>
        ))}
      </ul>
    </div>
  );
}
