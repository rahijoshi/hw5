import { useEffect, useRef } from "react";
import type { AuditEvent } from "../types";
import { agentMeta } from "../agentMeta";

function shortToolName(name: string | null): string | null {
  if (!name) return null;
  const withoutPrefix = name.replace(/^campus-customs_/, "");
  return withoutPrefix;
}

function formatArgValue(value: unknown): string {
  if (typeof value === "string") return value;
  return JSON.stringify(value);
}

function EventLine({ event }: { event: AuditEvent }) {
  const meta = agentMeta(event.agent);
  const tool = shortToolName(event.tool_name);
  const isAwaiting = event.stop_reason === "awaiting_human_approval";
  const isFailure = (event.stop_reason ?? "").startsWith("failed:");

  return (
    <li className={`feed-line${isAwaiting ? " feed-line-awaiting" : ""}${isFailure ? " feed-line-failed" : ""}`}>
      <span className="feed-line-dot" style={{ background: meta.color }} />
      <div className="feed-line-body">
        <div className="feed-line-head">
          <span style={{ color: meta.color, fontWeight: 600 }}>{meta.label}</span>
          {tool && <code className="feed-line-tool">{tool}()</code>}
          <span className="feed-line-time">
            {new Date(event.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
          </span>
        </div>
        {tool ? (
          <div className="feed-line-detail">
            {event.tool_args && Object.keys(event.tool_args).length > 0 && (
              <span className="feed-line-args">
                {Object.entries(event.tool_args)
                  .map(([k, v]) => `${k}: ${formatArgValue(v)}`)
                  .join("  ·  ")}
              </span>
            )}
            {isAwaiting ? (
              <span className="feed-line-awaiting-note">waiting on a human to approve this &rarr;</span>
            ) : (
              event.tool_result_summary && <span className="feed-line-result">{event.tool_result_summary}</span>
            )}
          </div>
        ) : (
          event.thoughts && <div className="feed-line-thoughts">{event.thoughts}</div>
        )}
        {isFailure && <div className="feed-line-error">{event.stop_reason}</div>}
      </div>
    </li>
  );
}

export function AgentFeed({ events }: { events: AuditEvent[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [events.length]);

  if (events.length === 0) {
    return <div className="feed-empty">No activity yet on this ticket. Start the agents to watch them work.</div>;
  }

  return (
    <div className="agent-feed">
      <ul className="feed-list">
        {events.map((event, index) => (
          <EventLine key={`${event.run_id}-${event.agent}-${event.iteration}-${index}`} event={event} />
        ))}
      </ul>
      <div ref={bottomRef} />
    </div>
  );
}
