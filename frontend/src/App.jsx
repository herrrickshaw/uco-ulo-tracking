import { useState } from "react";
import Collections from "./pages/Collections";
import Compliance from "./pages/Compliance";
import Dashboard from "./pages/Dashboard";
import Integrity from "./pages/Integrity";
import Lots from "./pages/Lots";
import Shipments from "./pages/Shipments";

const VIEWS = [
  { key: "dashboard", label: "Dashboard", component: Dashboard },
  { key: "collections", label: "Collections", component: Collections },
  { key: "lots", label: "Lots & Processing", component: Lots },
  { key: "shipments", label: "Shipments", component: Shipments },
  { key: "integrity", label: "Integrity Flags", component: Integrity },
  { key: "compliance", label: "EPR & GHG", component: Compliance },
];

export default function App() {
  const [active, setActive] = useState("dashboard");
  const ActiveComponent = VIEWS.find((v) => v.key === active)?.component ?? Dashboard;
  return (
    <div className="min-h-screen">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-3">
          <h1 className="text-xl font-bold text-slate-900">UCO / ULO Tracking</h1>
          <nav className="mt-3 flex flex-wrap gap-1">
            {VIEWS.map((v) => (
              <button
                key={v.key}
                onClick={() => setActive(v.key)}
                className={`rounded px-3 py-1.5 text-sm font-medium ${active === v.key ? "bg-slate-900 text-white" : "text-slate-600 hover:bg-slate-100"}`}
              >
                {v.label}
              </button>
            ))}
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        <ActiveComponent />
      </main>
    </div>
  );
}
