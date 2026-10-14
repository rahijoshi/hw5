import type { CashBalance } from "../types";
import { CashWidget } from "./CashWidget";

interface Props {
  cash: CashBalance | null;
  onReset: () => void;
  resetting: boolean;
}

export function Header({ cash, onReset, resetting }: Props) {
  return (
    <header className="app-header">
      <div className="app-header-title">
        <span className="app-header-flower" aria-hidden>
          &#10047;
        </span>
        <div>
          <h1>Campus Customs &mdash; ops desk</h1>
          <p>Watch the agent team work the board, and sign off on anything that touches cash.</p>
        </div>
      </div>
      <div className="app-header-right">
        <CashWidget cash={cash} />
        <button className="btn btn-ghost btn-small" onClick={onReset} disabled={resetting}>
          {resetting ? "Resetting…" : "Reset board"}
        </button>
      </div>
    </header>
  );
}
