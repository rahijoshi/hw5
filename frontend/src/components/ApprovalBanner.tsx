import { useState } from "react";
import type { AuditEvent } from "../types";
import { approvePayment } from "../api";
import { agentMeta } from "../agentMeta";

interface Props {
  pending: AuditEvent[];
  onApproved: () => void;
  onJumpToTicket: (ticketId: number) => void;
}

export function ApprovalBanner({ pending, onApproved, onJumpToTicket }: Props) {
  const [openFor, setOpenFor] = useState<number | null>(null);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  if (pending.length === 0) return null;

  async function handleApprove(ticketId: number) {
    if (!name.trim()) {
      setError("Sign your name first.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await approvePayment(ticketId, name.trim());
      setOpenFor(null);
      setName("");
      onApproved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Approval failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="approval-banner">
      {pending.map((item) => {
        const args = item.tool_args ?? {};
        const amount = typeof args.amount === "number" ? args.amount : null;
        const meta = agentMeta(item.agent);
        const isOpen = openFor === item.ticket_id;
        return (
          <div key={item.ticket_id} className="approval-slip">
            <div className="approval-slip-stamp" style={{ background: meta.color }}>
              signature needed
            </div>
            <div className="approval-slip-body">
              <p className="approval-slip-text">
                <button className="link-button" onClick={() => onJumpToTicket(item.ticket_id)}>
                  Ticket #{item.ticket_id}
                </button>{" "}
                &mdash; {meta.label} drafted a {String(args.kind ?? "payment")} of{" "}
                <strong>{amount !== null ? `$${amount.toFixed(2)}` : "?"}</strong> from{" "}
                <code>{String(args.account ?? "checking")}</code>. It will not go through without your
                signature.
              </p>
              {isOpen ? (
                <div className="approval-slip-form">
                  <input
                    autoFocus
                    placeholder="Your name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && handleApprove(item.ticket_id)}
                  />
                  <button className="btn btn-yellow" disabled={busy} onClick={() => handleApprove(item.ticket_id)}>
                    {busy ? "Signing…" : "Sign & approve"}
                  </button>
                  <button className="btn btn-ghost" onClick={() => setOpenFor(null)}>
                    Cancel
                  </button>
                </div>
              ) : (
                <button className="btn btn-yellow" onClick={() => setOpenFor(item.ticket_id)}>
                  Review &amp; approve
                </button>
              )}
              {isOpen && error && <p className="approval-slip-error">{error}</p>}
            </div>
          </div>
        );
      })}
    </div>
  );
}
