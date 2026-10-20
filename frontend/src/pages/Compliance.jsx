import { fetchEPR, fetchGHG, fetchRecyclerSupply } from "../api/client";
import DataTable from "../components/DataTable";
import useLoad from "../components/useLoad";

export default function Compliance() {
  const { data, error } = useLoad(fetchEPR, fetchRecyclerSupply, fetchGHG);
  if (error) return <div className="text-rose-600">{error}</div>;
  if (!data) return <div className="text-slate-400">Loading...</div>;
  const [epr, supply, ghg] = data;
  return (
    <div className="space-y-6">
      <section className="space-y-2">
        <h2 className="text-lg font-semibold">ULO - used-oil EPR (producers)</h2>
        <DataTable
          columns={[
            { key: "producer", label: "Producer" },
            { key: "fy", label: "FY" },
            { key: "target_pct", label: "Target %" },
            { key: "required_tonnes", label: "Required (t)" },
            { key: "certificates_tonnes", label: "Certificates (t)" },
            { key: "shortfall_tonnes", label: "Shortfall (t)" },
            { key: "compliant", label: "Status", render: (r) => (r.compliant ? "Compliant" : "Short") },
          ]}
          rows={epr}
        />
      </section>
      <section className="space-y-2">
        <h2 className="text-lg font-semibold">ULO - tonnes re-refined by recycler</h2>
        <DataTable columns={[{ key: "recycler", label: "Recycler" }, { key: "recycled_tonnes", label: "Recycled (t)" }]} rows={supply} />
      </section>
      <section className="space-y-2">
        <h2 className="text-lg font-semibold">UCO - indicative GHG savings vs fossil diesel</h2>
        <DataTable
          columns={[
            { key: "batch", label: "Batch" },
            { key: "product", label: "Product" },
            { key: "output_kg", label: "Output (kg)" },
            { key: "intensity_g_per_mj", label: "gCO2e/MJ" },
            { key: "savings_pct", label: "Saving %" },
            { key: "tco2e_saved", label: "tCO2e saved" },
          ]}
          rows={ghg}
        />
      </section>
    </div>
  );
}
