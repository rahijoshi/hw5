import type { AuditEvent } from "../types";
import { AGENT_META, agentMeta } from "../agentMeta";
import { AgentBadge } from "./AgentBadge";

interface AgentDigest {
  agent: string;
  finalWords: string | null;
  toolsUsed: string[];
}

function digestByAgent(events: AuditEvent[]): AgentDigest[] {
  const order = Object.keys(AGENT_META);
  const byAgent = new Map<string, AuditEvent[]>();
  for (const event of events) {
    if (!byAgent.has(event.agent)) byAgent.set(event.agent, []);
    byAgent.get(event.agent)!.push(event);
  }

  const agents = [...byAgent.keys()].sort((a, b) => order.indexOf(a) - order.indexOf(b));

  return agents.map((agent) => {
    const agentEvents = byAgent.get(agent)!;
    const finalEvent = [...agentEvents].reverse().find((e) => e.stop_reason === "completed" && !e.tool_name);
    const toolsUsed = [
      ...new Set(
        agentEvents
          .map((e) => e.tool_name)
          .filter((name): name is string => Boolean(name))
          .map((name) => name.replace(/^campus-customs_/, "")),
      ),
    ];
    return { agent, finalWords: finalEvent?.thoughts ?? null, toolsUsed };
  });
}

export function AgentSummary({ events }: { events: AuditEvent[] }) {
  const digests = digestByAgent(events);
  if (digests.length === 0) return null;

  return (
    <div className="agent-summary">
      <h3 className="agent-summary-title">What each agent did</h3>
      <div className="agent-summary-grid">
        {digests.map((digest) => (
          <div
            key={digest.agent}
            className="agent-summary-card"
            style={{ borderColor: agentMeta(digest.agent).color }}
          >
            <AgentBadge agent={digest.agent} />
            {digest.toolsUsed.length > 0 && (
              <div className="agent-summary-tools">
                {digest.toolsUsed.map((tool) => (
                  <code key={tool}>{tool}</code>
                ))}
              </div>
            )}
            <p className="agent-summary-words">
              {digest.finalWords ?? "Still working, or delegated without a final written report."}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}
