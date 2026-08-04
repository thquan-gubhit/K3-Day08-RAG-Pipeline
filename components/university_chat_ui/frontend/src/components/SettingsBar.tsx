import { Eye, Gauge, Sparkles, Trash2, Waves } from "lucide-react";
import type { UISettings } from "../types";
import { cn } from "../lib/utils";

type Props = {
  settings: UISettings;
  scoreThreshold: number;
  onChange: (patch: Partial<UISettings>) => void;
  onClearHistory: () => void;
};

function Toggle({
  label,
  checked,
  icon: Icon,
  onChange,
}: {
  label: string;
  checked: boolean;
  icon: typeof Eye;
  onChange: (next: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={cn(
        "chip transition",
        checked ? "border-cyan-brand/45 text-cyan-brand" : "hover:border-white/25",
      )}
    >
      <Icon size={11} aria-hidden="true" />
      {label}
      <span
        aria-hidden="true"
        className={cn(
          "ml-0.5 h-1.5 w-1.5 rounded-full",
          checked ? "bg-cyan-brand" : "bg-white/25",
        )}
      />
    </button>
  );
}

export default function SettingsBar({ settings, scoreThreshold, onChange, onClearHistory }: Props) {
  return (
    <div className="panel space-y-2.5 p-3">
      <div>
        <label
          htmlFor="rag-topk"
          className="mb-1 flex items-center justify-between text-[11.5px] text-muted"
        >
          <span className="flex items-center gap-1.5">
            <Gauge size={12} aria-hidden="true" /> Số chunks retrieval (top_k)
          </span>
          <span className="font-mono text-cyan-brand">{settings.topK}</span>
        </label>
        <input
          id="rag-topk"
          type="range"
          min={3}
          max={10}
          step={1}
          value={settings.topK}
          onChange={(e) => onChange({ topK: Number(e.target.value) })}
          className="w-full accent-[#22D3EE]"
          aria-valuemin={3}
          aria-valuemax={10}
          aria-valuenow={settings.topK}
        />
      </div>

      <div className="flex flex-wrap gap-1.5">
        <Toggle
          label="Điểm số"
          icon={Eye}
          checked={settings.showScores}
          onChange={(v) => onChange({ showScores: v })}
        />
        <Toggle
          label="Pipeline trace"
          icon={Sparkles}
          checked={settings.showTrace}
          onChange={(v) => onChange({ showTrace: v })}
        />
        <Toggle
          label="Giảm chuyển động"
          icon={Waves}
          checked={settings.reducedMotion}
          onChange={(v) => onChange({ reducedMotion: v })}
        />
        <button
          type="button"
          onClick={onClearHistory}
          aria-label="Xóa lịch sử hội thoại"
          className="chip transition hover:border-danger/45 hover:text-danger"
        >
          <Trash2 size={11} aria-hidden="true" /> Xóa lịch sử
        </button>
      </div>

      {/* Threshold hiển thị read-only: cho người dùng sửa sẽ làm sai logic fallback ở Task 9. */}
      <p className="text-[10.5px] text-muted">
        Ngưỡng fallback (chỉ đọc): cosine &lt; {scoreThreshold.toFixed(2)} → PageIndex
      </p>
    </div>
  );
}
