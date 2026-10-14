import { useEffect, useRef, useState } from "react";
import type { CashBalance } from "../types";

const formatter = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });

export function CashWidget({ cash }: { cash: CashBalance | null }) {
  const [flash, setFlash] = useState(false);
  const previous = useRef<number | null>(null);

  useEffect(() => {
    if (cash === null) return;
    if (previous.current !== null && previous.current !== cash.balance) {
      setFlash(true);
      const t = setTimeout(() => setFlash(false), 1200);
      return () => clearTimeout(t);
    }
    previous.current = cash.balance;
  }, [cash]);

  useEffect(() => {
    if (cash !== null) previous.current = cash.balance;
  }, [cash?.balance]);

  return (
    <div className={`cash-widget${flash ? " cash-widget-flash" : ""}`}>
      <span className="cash-widget-label">Checking</span>
      <span className="cash-widget-amount">
        {cash ? formatter.format(cash.balance) : "—"}
      </span>
    </div>
  );
}
