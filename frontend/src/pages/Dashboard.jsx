import { fetchSummary } from "../api/client";
import KpiCard from "../components/KpiCard";
import useLoad from "../components/useLoad";

export default function Dashboard() {
  const { data, error } = useLoad(fetchSummary);
  if (error) return <div className="text-rose-600">Failed to load: {error}</div>;
  if (!data) return <div className="text-slate-400">Loading...</div>;
  const [s] = data;
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <KpiCard label="UCO collected" value={`${s.uco_collected_tonnes} t`} />
      <KpiCard label="ULO collected" value={`${s.ulo_collected_tonnes} t`} />
      <KpiCard
        label="Integrity flags"
        value={s.integrity_flags_total}
        sublabel={`${s.integrity_flags_high} high severity`}
        tone={s.integrity_flags_high ? "bad" : "good"}
      />
      <KpiCard
        label="Custody ledger"
        value={s.ledger_intact ? "Intact" : "TAMPERED"}
        sublabel={`${s.ledger_entries} hash-chained entries`}
        tone={s.ledger_intact ? "good" : "bad"}
      />
      {Object.entries(s.output_tonnes_by_product).map(([k, v]) => (
        <KpiCard key={k} label={`Output: ${k.replace("_", " ")}`} value={`${v} t`} />
      ))}
    </div>
  );
}
