import type { Ticket } from "../types";
import { TICKET_TYPE_LABEL } from "../agentMeta";
import { StatusPill } from "./StatusPill";

interface Props {
  tickets: Ticket[];
  selectedId: number | null;
  runningIds: Set<number>;
  onSelect: (id: number) => void;
}

export function TicketList({ tickets, selectedId, runningIds, onSelect }: Props) {
  return (
    <div className="ticket-list">
      {tickets.map((ticket) => (
        <button
          key={ticket.id}
          className={`ticket-card${ticket.id === selectedId ? " ticket-card-selected" : ""}`}
          onClick={() => onSelect(ticket.id)}
        >
          <div className="ticket-card-top">
            <span className="ticket-card-id">#{ticket.id}</span>
            <StatusPill status={ticket.status} />
          </div>
          <div className="ticket-card-subject">{ticket.subject}</div>
          <div className="ticket-card-meta">
            {TICKET_TYPE_LABEL[ticket.type] ?? ticket.type} &middot; {ticket.requester}
          </div>
          {runningIds.has(ticket.id) && (
            <div className="ticket-card-running">
              <span className="pulse-dot" /> agents working&hellip;
            </div>
          )}
        </button>
      ))}
    </div>
  );
}
