export type TicketStatus = "open" | "pending_approval" | "blocked" | "resolved";

export interface Ticket {
  id: number;
  type: string;
  requester: string;
  subject: string;
  sku: string | null;
  size: string | null;
  qty: number | null;
  lease_id: number | null;
  invoice_id: number | null;
  status: TicketStatus;
  notes: string | null;
  created_at: string;
  is_resolved: boolean;
}

export type AgentName =
  | "boss"
  | "inventory"
  | "accounting"
  | "facilities"
  | "customer_service";

export interface AuditEvent {
  run_id: string;
  ticket_id: number;
  agent: AgentName | string;
  timestamp: string;
  iteration: number;
  thoughts: string;
  tool_name: string | null;
  tool_args: Record<string, unknown> | null;
  tool_result_summary: string | null;
  stop_reason: string | null;
}

export interface CashBalance {
  found: boolean;
  name: string;
  balance: number;
  date: string;
}

export interface ApprovePaymentResult {
  ok: boolean;
  payment: {
    id: number;
    kind: string;
    ref_id: number;
    amount: number;
    account: string;
    paid_at: string;
    approved_by: string;
  };
  new_balance: number;
}
