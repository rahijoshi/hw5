import { STATUS_META } from "../agentMeta";

export function StatusPill({ status }: { status: string }) {
  const meta = STATUS_META[status] ?? { label: status, color: "var(--ink-soft)", soft: "var(--lavender-1)" };
  return (
    <span
      className="status-pill"
      style={{ color: meta.color, background: meta.soft, borderColor: meta.color }}
    >
      {meta.label}
    </span>
  );
}
