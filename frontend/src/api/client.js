async function apiFetch(path, options = {}) {
  const res = await fetch(`/api${path}`, { headers: { "Content-Type": "application/json" }, ...options });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch {
      // ignore non-JSON error bodies
    }
    throw new Error(detail);
  }
  return res.json();
}

export const fetchSummary = () => apiFetch("/dashboard/summary");
export const fetchCollections = (material) => apiFetch(`/collections${material ? `?material=${material}` : ""}`);
export const fetchGenerators = () => apiFetch("/generators");
export const fetchCollectors = () => apiFetch("/collectors");
export const fetchLots = () => apiFetch("/lots");
export const fetchBatches = () => apiFetch("/batches");
export const fetchIntegrity = () => apiFetch("/compliance/integrity");
export const fetchEPR = () => apiFetch("/compliance/epr");
export const fetchRecyclerSupply = () => apiFetch("/compliance/epr/recycler-supply");
export const fetchGHG = () => apiFetch("/compliance/ghg");
