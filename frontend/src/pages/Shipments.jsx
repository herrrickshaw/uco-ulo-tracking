import { fetchCollectors, fetchShipments } from "../api/client";
import DataTable from "../components/DataTable";
import useLoad from "../components/useLoad";

const yn = (v) => (v ? "yes" : "NO");

export default function Shipments() {
  const { data, error } = useLoad(fetchShipments, fetchCollectors);
  if (error) return <div className="text-rose-600">{error}</div>;
  if (!data) return <div className="text-slate-400">Loading...</div>;
  const [rows, cols] = data;
  const name = (id) => cols.find((c) => c.id === id)?.name ?? id;
  const columns = [
    { key: "dispatched_on", label: "Dispatched" },
    { key: "manifest_no", label: "Manifest (Form 10)" },
    { key: "material", label: "Material" },
    { key: "sender_id", label: "From", render: (r) => name(r.sender_id) },
    { key: "receiver_id", label: "To", render: (r) => name(r.receiver_id) },
    { key: "vehicle_no", label: "Vehicle" },
    { key: "gps_tracked", label: "GPS", render: (r) => yn(r.gps_tracked) },
    { key: "nhwts_registered", label: "NHWTS", render: (r) => yn(r.nhwts_registered) },
    { key: "distance_km", label: "km" },
    { key: "dispatched_kg", label: "Sent (kg)" },
    { key: "received_kg", label: "Received (kg)" },
  ];
  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold">Shipments</h2>
      <DataTable columns={columns} rows={rows} />
    </div>
  );
}
