import { useState } from "react";
import { fetchCollections, fetchCollectors, fetchGenerators } from "../api/client";
import DataTable from "../components/DataTable";
import useLoad from "../components/useLoad";

export default function Collections() {
  const [material, setMaterial] = useState("");
  const { data, error } = useLoad(() => fetchCollections(), fetchGenerators, fetchCollectors);
  if (error) return <div className="text-rose-600">{error}</div>;
  if (!data) return <div className="text-slate-400">Loading...</div>;
  const [rows, gens, cols] = data;
  const name = (list, id) => list.find((x) => x.id === id)?.name ?? id;
  const shown = material ? rows.filter((r) => r.material === material) : rows;
  const columns = [
    { key: "collected_on", label: "Date" },
    { key: "manifest_no", label: "Manifest" },
    { key: "material", label: "Material" },
    { key: "generator_id", label: "Generator", render: (r) => name(gens, r.generator_id) },
    { key: "collector_id", label: "Collector", render: (r) => name(cols, r.collector_id) },
    { key: "quantity_litres", label: "Litres" },
    { key: "tpc_pct", label: "TPC %" },
    { key: "water_pct", label: "Water %" },
    { key: "pcb_ppm", label: "PCB ppm" },
  ];
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h2 className="text-lg font-semibold">Collections</h2>
        <select className="rounded border px-2 py-1 text-sm" value={material} onChange={(e) => setMaterial(e.target.value)}>
          <option value="">All</option>
          <option value="UCO">UCO</option>
          <option value="ULO">ULO</option>
        </select>
      </div>
      <DataTable columns={columns} rows={shown} />
    </div>
  );
}
