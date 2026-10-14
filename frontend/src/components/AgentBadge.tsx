import { agentMeta } from "../agentMeta";

export function AgentBadge({ agent }: { agent: string }) {
  const meta = agentMeta(agent);
  return (
    <span className="agent-badge" style={{ color: meta.color, background: meta.soft }}>
      <span className="agent-badge-glyph" style={{ background: meta.color }}>
        {meta.glyph}
      </span>
      {meta.label}
    </span>
  );
}
