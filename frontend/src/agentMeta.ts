export interface AgentMeta {
  label: string;
  glyph: string;
  color: string;
  soft: string;
}

export const AGENT_META: Record<string, AgentMeta> = {
  boss: { label: "Boss", glyph: "B", color: "var(--agent-boss)", soft: "var(--agent-boss-soft)" },
  inventory: {
    label: "Inventory",
    glyph: "I",
    color: "var(--agent-inventory)",
    soft: "var(--agent-inventory-soft)",
  },
  accounting: {
    label: "Accounting",
    glyph: "$",
    color: "var(--agent-accounting)",
    soft: "var(--agent-accounting-soft)",
  },
  facilities: {
    label: "Facilities",
    glyph: "F",
    color: "var(--agent-facilities)",
    soft: "var(--agent-facilities-soft)",
  },
  customer_service: {
    label: "Customer Service",
    glyph: "C",
    color: "var(--agent-customer_service)",
    soft: "var(--agent-customer_service-soft)",
  },
  "human-approval": {
    label: "Human approval",
    glyph: "✓",
    color: "var(--green)",
    soft: "var(--green-soft)",
  },
};

export function agentMeta(name: string): AgentMeta {
  return (
    AGENT_META[name] ?? {
      label: name,
      glyph: name.slice(0, 1).toUpperCase(),
      color: "var(--ink-soft)",
      soft: "var(--lavender-1)",
    }
  );
}

export const TICKET_TYPE_LABEL: Record<string, string> = {
  customer_order: "Customer order",
  rent_notice: "Rent notice",
  price_override: "Price override",
};

export const STATUS_META: Record<string, { label: string; color: string; soft: string }> = {
  open: { label: "Open", color: "var(--ink-soft)", soft: "var(--lavender-1)" },
  pending_approval: { label: "Needs approval", color: "var(--yellow-ink)", soft: "var(--yellow-soft)" },
  blocked: { label: "Blocked", color: "var(--red)", soft: "var(--red-soft)" },
  resolved: { label: "Resolved", color: "var(--green)", soft: "var(--green-soft)" },
};
