import { useCallback, useEffect, useRef, useState } from "react";
import "./App.css";
import { getCash, getEvents, getPendingPayments, getTickets, resetDatabase, runTicket } from "./api";
import type { AuditEvent, CashBalance, Ticket } from "./types";
import { Header } from "./components/Header";
import { TicketList } from "./components/TicketList";
import { TicketDesk } from "./components/TicketDesk";
import { ApprovalBanner } from "./components/ApprovalBanner";

const POLL_MS = 2000;

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [pending, setPending] = useState<AuditEvent[]>([]);
  const [cash, setCash] = useState<CashBalance | null>(null);
  const [runningIds, setRunningIds] = useState<Set<number>>(new Set());
  const [resetting, setResetting] = useState(false);
  const [bannerError, setBannerError] = useState<string | null>(null);

  const runningRef = useRef(runningIds);
  runningRef.current = runningIds;

  const refreshAll = useCallback(async (ticketIdForEvents: number | null) => {
    try {
      const [freshTickets, freshCash, freshPending] = await Promise.all([
        getTickets(),
        getCash(),
        getPendingPayments(),
      ]);
      setTickets(freshTickets);
      setCash(freshCash);
      setPending(freshPending);
      setBannerError(null);

      setRunningIds((prev) => {
        if (prev.size === 0) return prev;
        const next = new Set(prev);
        for (const ticket of freshTickets) {
          if (next.has(ticket.id) && ticket.status !== "open") next.delete(ticket.id);
        }
        return next;
      });

      if (ticketIdForEvents !== null) {
        const freshEvents = await getEvents(ticketIdForEvents);
        setEvents(freshEvents);
      }
    } catch (err) {
      setBannerError(err instanceof Error ? err.message : "Could not reach the backend on :8000.");
    }
  }, []);

  useEffect(() => {
    refreshAll(selectedId);
    const interval = setInterval(() => refreshAll(selectedId), POLL_MS);
    return () => clearInterval(interval);
  }, [selectedId, refreshAll]);

  async function handleSelect(id: number) {
    setSelectedId(id);
    try {
      setEvents(await getEvents(id));
    } catch {
      // next poll tick will retry
    }
  }

  async function handleStart() {
    if (selectedId === null) return;
    try {
      await runTicket(selectedId);
      setRunningIds((prev) => new Set(prev).add(selectedId));
      setEvents([]);
    } catch (err) {
      setBannerError(err instanceof Error ? err.message : "Could not start the agent team.");
    }
  }

  async function handleReset() {
    setResetting(true);
    try {
      await resetDatabase();
      setSelectedId(null);
      setEvents([]);
      setRunningIds(new Set());
      await refreshAll(null);
    } catch (err) {
      setBannerError(err instanceof Error ? err.message : "Reset failed.");
    } finally {
      setResetting(false);
    }
  }

  const selectedTicket = tickets.find((t) => t.id === selectedId) ?? null;

  return (
    <div className="app-shell">
      <Header cash={cash} onReset={handleReset} resetting={resetting} />

      {bannerError && <div className="connection-error">{bannerError}</div>}

      <ApprovalBanner pending={pending} onApproved={() => refreshAll(selectedId)} onJumpToTicket={handleSelect} />

      <main className="app-main">
        <TicketList
          tickets={tickets}
          selectedId={selectedId}
          runningIds={runningIds}
          onSelect={handleSelect}
        />
        <TicketDesk
          ticket={selectedTicket}
          events={events}
          isRunning={selectedId !== null && runningIds.has(selectedId)}
          onStart={handleStart}
        />
      </main>
    </div>
  );
}
