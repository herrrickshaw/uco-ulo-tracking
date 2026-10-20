# Platform review: what we borrowed and what is still missing

Reviewed 2026-10-20. "Veloce" returned no results in search -- if you meant a specific vendor, send a URL.

| Source | What it does | What we took |
|---|---|---|
| **CPCB Used-Oil EPR portal** (eprusedoil.cpcb.gov.in) | Registers producers (P1-P9), recyclers/co-processors, importers, collection agents (CA-1/CA-2); generates recycler EPR certificates `QEPR = Qp x CF x Wp`; public dashboard of applications, targets and per-recycler certificates Generated / Transferred / Available (MT); quarterly + annual returns; Environmental Compensation. | Real EPR schedule (Y-2 base, 5/10/20/20/40/40/50%), certificate formula and weightage (1.0 re-refining, 0.25 co-processing), 2-year validity, purchase cap (liability + 10%), recycler-only transfers, price band (30-100% of EC), CA-1/CA-2 rules, return due dates, certificate ledger view. |
| **CPCB collection-agent guidelines (Jan 2025)** | Form 10 seven-copy manifest, Form 8 labels, GPS vehicles, NHWTS registration, SPCB intimation, CA-1 <= 200 L containers and 75/150 km radius. | `Shipment` model + checks: `vehicle_not_in_nhwts`, `vehicle_no_gps`, `spcb_not_intimated`, `ca1_*`, `transit_variance`. |
| **FSSAI RUCO traceability app** | FBO disposal requests, NFP unit enrolment, aggregator recognition, real-time reports. | `ruco_request_id` on collections, registration validity checks, TPC capture. No public API found, so no ingestion. |
| **Veriflux (US)** | Per-pickup address validation, routing/dispatch, manifests tied to compliance, "separated food waste" evidence for EPA/45Z/LCFS/ISCC. | Per-pickup records with evidence refs and generator coordinates; mass balance; fraud checks. Routing/dispatch not built. |
| **Recycle Ledger (Korea)** | Blockchain record per UCO step; AI image recognition, IoT scales, RFID. | Hash-chained custody ledger; `evidence_ref` (scale/ticket ID). No IoT/AI. |
| **Bioledger / RSB** | Blockchain provenance for biofuel feedstock, piloted with UCO partners. | Same ledger idea. Ours is single-node tamper-*evident*, not a distributed ledger. |
| **Ecoil / Byufuel (India)** | Private UCO aggregation + traceability apps. Claims are self-described. | Aggregator -> processor lot model. |

## Still missing
Portal/RUCO data ingestion (no public API), route planning, IoT/photo evidence upload, Environmental Compensation
amounts (EC INR/t not captured: `EC_INR_PER_TONNE` is None until confirmed), producer-to-producer re-allocation of
targets, importer flow, India Schedule V numeric limits, authentication, audit users, PDF/Excel reports.
