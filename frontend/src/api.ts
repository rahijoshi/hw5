import type { AuditEvent, CashBalance, Ticket } from "./types";

// The backend is a fixed local dev server for this homework, never
// deployed elsewhere, so a hardcoded base URL is simpler than an env var.
const BASE_URL = "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(body.detail ?? `Request to ${path} failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export function getTickets(): Promise<Ticket[]> {
  return request<Ticket[]>("/api/tickets");
}

export function runTicket(ticketId: number): Promise<{ status: string; ticket_id: number }> {
  return request(`/api/tickets/${ticketId}/run`, { method: "POST" });
}

export function getEvents(ticketId?: number, limit = 300): Promise<AuditEvent[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (ticketId !== undefined) params.set("ticket_id", String(ticketId));
  return request<AuditEvent[]>(`/api/events?${params.toString()}`);
}

export function getPendingPayments(): Promise<AuditEvent[]> {
  return request<AuditEvent[]>("/api/payments/pending");
}

export function approvePayment(ticketId: number, approvedBy: string) {
  return request("/api/payments/approve", {
    method: "POST",
    body: JSON.stringify({ ticket_id: ticketId, approved_by: approvedBy }),
  });
}

export function getCash(account = "checking"): Promise<CashBalance> {
  return request<CashBalance>(`/api/cash?account=${encodeURIComponent(account)}`);
}

export function resetDatabase(): Promise<{ ok: boolean }> {
  return request("/api/reset", { method: "POST" });
}
