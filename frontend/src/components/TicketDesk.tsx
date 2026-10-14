import type { AuditEvent, Ticket } from "../types";
import { TICKET_TYPE_LABEL } from "../agentMeta";
import { StatusPill } from "./StatusPill";
import { AgentFeed } from "./AgentFeed";
import { AgentSummary } from "./AgentSummary";

interface Props {
  ticket: Ticket | null;
  events: AuditEvent[];
  isRunning: boolean;
  onStart: () => void;
}

const FACT_FIELDS: Array<[keyof Ticket, string]> = [
  ["sku", "sku"],
  ["size", "size"],
  ["qty", "qty"],
  ["lease_id", "lease_id"],
  ["invoice_id", "invoice_id"],
];

export function TicketDesk({ ticket, events, isRunning, onStart }: Props) {
  if (!ticket) {
    return (
      <div className="ticket-desk ticket-desk-empty">
        <p>Pick a ticket from the board to open it on the desk.</p>
      </div>
    );
  }

  const facts = FACT_FIELDS.filter(([key]) => ticket[key] !== null && ticket[key] !== undefined);
  const hasRun = events.length > 0;

  return (
    <div className="ticket-desk">
      <header className="ticket-desk-header">
        <div>
          <div className="ticket-desk-kicker">
            {TICKET_TYPE_LABEL[ticket.type] ?? ticket.type} &middot; {ticket.requester}
          </div>
          <h2>
            #{ticket.id} &mdash; {ticket.subject}
          </h2>
        </div>
        <StatusPill status={ticket.status} />
      </header>

      {facts.length > 0 && (
        <div className="ticket-desk-facts">
          {facts.map(([key, label]) => (
            <div key={key} className="fact">
              <span className="fact-k">{label}</span>
              <span className="fact-v">{String(ticket[key])}</span>
            </div>
          ))}
        </div>
      )}

      {ticket.notes && <p className="ticket-desk-notes">{ticket.notes}</p>}

      <div className="ticket-desk-actions">
        <button className="btn btn-primary" disabled={isRunning} onClick={onStart}>
          {isRunning ? (
            <>
              <span className="pulse-dot pulse-dot-light" /> Agents working&hellip;
            </>
          ) : hasRun ? (
            "Re-run agents"
          ) : (
            "Start agents"
          )}
        </button>
      </div>

      <div className="ticket-desk-feed-label">Agent activity</div>
      <AgentFeed events={events} />

      {!isRunning && hasRun && <AgentSummary events={events} />}
    </div>
  );
}
