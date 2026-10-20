# UCO / ULO Tracking

Chain-of-custody and compliance tracking for **Used Cooking Oil (UCO)** and **Used Lubricating Oil (ULO)** in India.
Sister project to [saf-monitoring-system](https://github.com/herrrickshaw/saf-monitoring-system) and built on the same
stack (FastAPI + SQLite, React/Vite/Tailwind, mock-data seeding). UCO is a feedstock for biodiesel and SAF (HEFA);
ULO is a hazardous waste that is re-refined into base oil.

```
generator -> collection (manifest) -> aggregator lot -> processing batch -> dispatch
 (restaurant / garage)   TPC, water, PCB     mass balance     yield check     buyer
```

## What it does

| Area | UCO | ULO |
|---|---|---|
| Source registry | FBOs with FSSAI licence, declared monthly oil purchase | Garages/industry with CPCB authorisation |
| Collection record | manifest no., litres, TPC %, FFA % | manifest no., litres, water %, PCB ppm, chlorine ppm |
| Lot mass balance | kg received vs kg processed per lot | same |
| Processing | biodiesel / pretreated HEFA feedstock, yield-range check | base oil / fuel oil, yield-range check |
| Compliance | FSSAI RUCO context, indicative GHG saving vs fossil diesel | Used-oil EPR: producer obligation vs certificates bought, recycler supply |

### Integrity checks (`backend/app/calculations/integrity.py`)
Heuristic fraud/data-quality flags. A flag is a prompt to investigate, not a finding.
`suspiciously_fresh_uco` (TPC far below used-oil range, the classic UCO-fraud signature), `generator_over_capacity`
(collected more than the generator could plausibly return given declared purchases), `duplicate_manifest`,
`collector_registration` (missing/expired), `mass_balance`, `implausible_yield`, `product_mismatch`,
`dispatch_exceeds_output`, `pcb_hazard_segregate`, `high_water`, `high_chlorine`.

## Regulatory disclaimer

Every threshold lives in `backend/app/calculations/constants.py` as an **editable default, not hardcoded truth**
(also served at `GET /api/compliance/parameters`). Values marked VERIFY or PLACEHOLDER there must be reconciled with
the official source before real compliance use.

- **FSSAI**: 25% TPC ceiling for frying oil (FSS Licensing & Registration First Amendment 2017); RUCO traceability
  application; >50 L/day record-keeping comes from a May 2019 order known only via a press notice -- check the original.
- **Used-oil EPR**: HOWM Second Amendment Rules 2023, G.S.R. 677(E), effective 1 Apr 2024, as reproduced in CPCB's
  Used Oil FAQ: producer target = 5/10/20/20/40/40% (FY2024-25 to 2029-30), 50% from 2030-31, each of sales/imports two
  years earlier (Y-2); used-oil importers 100% of Y-1 imports. Certificates `QEPR = Qp x CF x Wp` (Wp 1.0 re-refining,
  0.25 co-processing; CF is set per recycler by CPCB -- our default is a placeholder), valid two years after the FY end,
  purchase cap = liability + 10%, not tradable between producers. EC (Environmental Compensation) INR/t is not captured.
- **GHG defaults** are indicative RED-style values, not CORSIA/RED III certified numbers.
- Fraud heuristics (fresh-oil TPC floor, recoverable fraction) are analytical choices, not regulation.

## Demos

* **Interactive demo (Lovable, mock data):** https://uco-ulo-tracking-demo.lovable.app -- front-end only; includes a live SHA-256 ledger you can tamper with. ([editor](https://lovable.dev/projects/286329ce-3fce-4673-b440-fab690ef6b1f), owner only.)
* **Narrated walkthrough (2m33s):** https://youtu.be/mVYgWein8Xo -- real captured output from the running API and test suite.

## Benchmarks and references

* [docs/PLATFORM_REVIEW.md](docs/PLATFORM_REVIEW.md) -- CPCB EPR portal, FSSAI RUCO, Veriflux, Recycle Ledger, Bioledger: what was borrowed, what is missing.
* [docs/QUALITY_REQUIREMENTS.md](docs/QUALITY_REQUIREMENTS.md) -- UCO / ULO quality requirements across countries, with confidence tags.

New in v0.2: shipments with Form 10 / GPS / NHWTS / CA-1 checks, EPR certificate ledger and transfer rules, return-filing
tracker, and a SHA-256 hash-chained custody ledger (`GET /api/compliance/ledger`) that detects edits to logged records.
The ledger is tamper-*evident* on one node; anchor the head hash externally for stronger guarantees.

## Run

```bash
./run_app.sh            # backend :8000 (docs at /docs), frontend :5173
cd backend && source .venv/bin/activate && pytest
```

First start seeds six months of mock data for 8 generators, 7 collectors/processors, 12 lots, 12 batches and 14 shipments with
anomalies planted deliberately so each check has something to show, plus two EPR producers (one compliant, one short).

## Not built yet
See the end of docs/PLATFORM_REVIEW.md.
