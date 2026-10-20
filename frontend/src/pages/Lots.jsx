import { fetchBatches, fetchLots } from "../api/client";
import DataTable from "../components/DataTable";
import useLoad from "../components/useLoad";

export default function Lots() {
  const { data, error } = useLoad(fetchLots, fetchBatches);
  if (error) return <div className="text-rose-600">{error}</div>;
  if (!data) return <div className="text-slate-400">Loading...</div>;
  const [lots, batches] = data;
  const lotColumns = [
    { key: "lot_code", label: "Lot" },
    { key: "material", label: "Material" },
    { key: "aggregator", label: "Aggregator" },
    { key: "n_collections", label: "Collections" },
    { key: "received_kg", label: "Received (kg)" },
    { key: "processed_kg", label: "Processed (kg)" },
    { key: "balanced", label: "Mass balance", render: (r) => (r.balanced ? "OK" : "OVER-PROCESSED") },
  ];
  const batchColumns = [
    { key: "batch_code", label: "Batch" },
    { key: "product", label: "Product" },
    { key: "input_kg", label: "Input (kg)" },
    { key: "output_kg", label: "Output (kg)" },
    { key: "yield", label: "Yield", render: (r) => `${((r.output_kg / r.input_kg) * 100).toFixed(0)}%` },
  ];
  return (
    <div className="space-y-6">
      <section className="space-y-2"><h2 className="text-lg font-semibold">Lots &amp; mass balance</h2><DataTable columns={lotColumns} rows={lots} /></section>
      <section className="space-y-2"><h2 className="text-lg font-semibold">Processing batches</h2><DataTable columns={batchColumns} rows={batches} /></section>
    </div>
  );
}
