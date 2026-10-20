import { fetchCertificateLedger, fetchEPR, fetchGHG, fetchRecyclerSupply, fetchReturns } from "../api/client";
import DataTable from "../components/DataTable";
import useLoad from "../components/useLoad";

export default function Compliance() {
  const { data, error } = useLoad(fetchEPR, fetchRecyclerSupply, fetchGHG, fetchCertificateLedger, fetchReturns);
  if (error) return <div className="text-rose-600">{error}</div>;
  if (!data) return <div className="text-slate-400">Loading...</div>;
  const [epr, supply, ghg, certs, returns] = data;
  return (
    <div className="space-y-6">
      <section className="space-y-2">
        <h2 className="text-lg font-semibold">ULO - used-oil EPR (producers)</h2>
        <DataTable
          columns={[
            { key: "producer", label: "Producer" },
            { key: "fy", label: "FY" },
            { key: "producer_type", label: "Type" },
            { key: "basis_fy", label: "Base year (Y-2)" },
            { key: "target_pct", label: "Target %" },
            { key: "required_tonnes", label: "Required (t)" },
            { key: "max_purchasable_tonnes", label: "Buy cap (t)" },
            { key: "certificates_tonnes", label: "Certificates (t)" },
            { key: "shortfall_tonnes", label: "Shortfall (t)" },
            { key: "compliant", label: "Status", render: (r) => (r.compliant ? "Compliant" : "Short") },
          ]}
          rows={epr}
        />
      </section>
      <section className="space-y-2">
        <h2 className="text-lg font-semibold">ULO - EPR certificate ledger (as on the CPCB portal)</h2>
        <DataTable
          columns={[
            { key: "recycler", label: "Recycler" },
            { key: "generated_mt", label: "Generated (MT)" },
            { key: "transferred_mt", label: "Transferred (MT)" },
            { key: "available_mt", label: "Available (MT)" },
          ]}
          rows={certs}
        />
        <DataTable
          columns={[{ key: "recycler", label: "Recycler" }, { key: "route", label: "Route" }, { key: "end_product_tonnes", label: "End product (t)" }]}
          rows={supply}
        />
      </section>
      <section className="space-y-2">
        <h2 className="text-lg font-semibold">Quarterly / annual returns</h2>
        <DataTable
          columns={[
            { key: "entity", label: "Entity" },
            { key: "period", label: "Period" },
            { key: "due_on", label: "Due" },
            { key: "filed_on", label: "Filed" },
            { key: "status", label: "Status", render: (r) => <span className={r.status === "overdue" ? "font-semibold text-rose-600" : ""}>{r.status}</span> },
          ]}
          rows={returns}
        />
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
