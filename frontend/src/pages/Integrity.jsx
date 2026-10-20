import { fetchIntegrity } from "../api/client";
import DataTable from "../components/DataTable";
import useLoad from "../components/useLoad";

export default function Integrity() {
  const { data, error } = useLoad(fetchIntegrity);
  if (error) return <div className="text-rose-600">{error}</div>;
  if (!data) return <div className="text-slate-400">Loading...</div>;
  const columns = [
    { key: "severity", label: "Severity", render: (r) => <span className={r.severity === "high" ? "font-semibold text-rose-600" : "text-amber-600"}>{r.severity}</span> },
    { key: "check", label: "Check" },
    { key: "ref", label: "Reference" },
    { key: "detail", label: "Detail" },
  ];
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Integrity flags</h2>
      <p className="text-sm text-slate-500">Heuristic fraud and data-quality checks. A flag is a prompt to investigate, not a finding.</p>
      <DataTable columns={columns} rows={data[0]} emptyMessage="No flags." />
    </div>
  );
}
