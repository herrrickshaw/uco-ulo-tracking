export default function KpiCard({ label, value, sublabel, tone = "default" }) {
  const toneClasses = {
    default: "border-slate-200 bg-white",
    good: "border-emerald-200 bg-emerald-50",
    bad: "border-rose-200 bg-rose-50",
  };

  return (
    <div className={`rounded-lg border p-4 shadow-sm ${toneClasses[tone]}`}>
      <div className="text-sm text-slate-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold text-slate-900">{value}</div>
      {sublabel && <div className="mt-1 text-xs text-slate-400">{sublabel}</div>}
    </div>
  );
}
