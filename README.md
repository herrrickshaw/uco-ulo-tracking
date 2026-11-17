# UCO / ULO Tracking

Chain-of-custody and compliance tracking for **Used Cooking Oil (UCO)** and **Used Lubricating Oil (ULO)** in India.
A FastAPI + SQLite backend and React/Vite/Tailwind dashboard, seeded with mock data, that records collections, lots,
processing batches, dispatches and shipments, runs fraud/data-quality checks, and models used-oil EPR obligations.
Sister project to [saf-monitoring-system](https://github.com/herrrickshaw/saf-monitoring-system), on the same stack.
UCO is a feedstock for biodiesel and SAF (HEFA); ULO is a hazardous waste that is re-refined into base oil.

> Status: research-only prototype on mock data. Regulatory thresholds are editable defaults, several marked
> VERIFY/PLACEHOLDER; not for real compliance use until reconciled with the official sources.

```
generator -> collection (manifest) -> aggregator lot -> processing batch -> dispatch
 (restaurant / garage)   TPC, water, PCB     mass balance     yield check     buyer
```

## What it does
- Registers sources (FBOs with FSSAI licence; garages/industry with CPCB authorisation) and records collections with manifest no., litres and quality readings (UCO: TPC, FFA; ULO: water, PCB, chlorine).
- Aggregates collections into lots, checks kg received vs processed, and checks batch yield ranges (biodiesel / HEFA feedstock for UCO; base oil / fuel oil for ULO).
- Tracks shipments with Form 10 / GPS / NHWTS / CA-1 checks.
- Models used-oil EPR: producer obligation vs certificates bought, recycler certificate ledger (Generated / Transferred / Available), return-filing tracker.
- Runs heuristic integrity checks (a flag is a prompt to investigate, not a finding).
- Keeps a SHA-256 hash-chained custody ledger (`GET /api/compliance/ledger`) that detects edits to logged records.

## Quick start
```bash
git clone https://github.com/herrrickshaw/uco-ulo-tracking.git
cd uco-ulo-tracking
./run_app.sh            # backend :8000 (docs at /docs), frontend :5173
```
`run_app.sh` needs Python 3.10+ (PEP 604 type hints) and Node. On first start it seeds six months of mock data: 8 generators, 7 collectors/processors, 12 lots, 12 batches, 14 shipments (anomalies planted deliberately so each check has something to show) and two EPR producers (one compliant, one short).

Demos: [interactive demo (Lovable, mock data, live tamperable ledger)](https://uco-ulo-tracking-demo.lovable.app) and a [narrated walkthrough (2m33s)](https://youtu.be/mVYgWein8Xo).

## How it works
| Stage | Module | Output |
|---|---|---|
| HTTP API | `backend/app/main.py`, `routers/{supply,compliance,dashboard}.py` | JSON under `/api` |
| Persistence | `backend/app/db.py`, `models.py` | SQLite file (`UCO_DB_PATH`) |
| Pure calculations | `backend/app/calculations/` | mass balance, yield, quality flags, EPR, GHG, returns, integrity, ledger |
| Mock data | `backend/app/seed/mock_data.py` | deterministic seed (`random.Random(42)`) |
| UI | `frontend/src/pages/*` | Dashboard, Collections, Lots, Shipments, Compliance, Integrity |

Calculations are pure functions over ORM rows so they can be unit-tested without a database; routers only load rows and shape responses.

### Integrity checks (`backend/app/calculations/integrity.py`)
`suspiciously_fresh_uco` (TPC far below used-oil range, the classic UCO-fraud signature), `generator_over_capacity`
(collected more than the generator could plausibly return given declared purchases), `duplicate_manifest`,
`collector_registration` (missing/expired), `mass_balance`, `implausible_yield`, `product_mismatch`,
`dispatch_exceeds_output`, `pcb_hazard_segregate`, `high_water`, `high_chlorine`, plus shipment checks
(`vehicle_not_in_nhwts`, `vehicle_no_gps`, `spcb_not_intimated`, `ca1_*`, `transit_variance`).

## Repository layout
| Path | Purpose |
|---|---|
| `backend/app/` | FastAPI app, models, calculations, routers, seed data |
| `backend/tests/` | pytest: unit tests, router smoke tests, seed-output characterisation test (`golden_seed_outputs.json`) |
| `frontend/` | React + Vite + Tailwind UI |
| `docs/PLATFORM_REVIEW.md` | CPCB EPR portal, FSSAI RUCO, Veriflux, Recycle Ledger, Bioledger: what was borrowed, what is missing |
| `docs/QUALITY_REQUIREMENTS.md` | UCO / ULO quality requirements across countries, with confidence tags |
| `run_app.sh` | starts backend and frontend together |

## Data sources
No external data is fetched; everything is seeded mock data. Regulatory parameters were taken from the sources below
and are documented, with confidence tags, in `docs/`.

| Source | What is taken | Caveat |
|---|---|---|
| FSSAI | 25% TPC ceiling for frying oil (FSS Licensing & Registration First Amendment 2017); RUCO traceability context | The >50 L/day record-keeping rule comes from a May 2019 order known only via a press notice: check the original |
| CPCB / HOWM Second Amendment Rules 2023, G.S.R. 677(E), effective 1 Apr 2024 | Used-oil EPR schedule as reproduced in CPCB's Used Oil FAQ | CF is set per recycler by CPCB; the default here is a placeholder |
| GHG defaults | Indicative RED-style values | Not CORSIA / RED III certified numbers |

Used-oil EPR in the model: producer target 5/10/20/20/40/40% (FY2024-25 to 2029-30), 50% from 2030-31, each of
sales/imports two years earlier (Y-2); used-oil importers 100% of Y-1 imports. Certificates `QEPR = Qp x CF x Wp`
(Wp 1.0 re-refining, 0.25 co-processing), valid two years after the FY end, purchase cap = liability + 10%, not
tradable between producers. Fraud heuristics (fresh-oil TPC floor, recoverable fraction) are analytical choices, not regulation.

## Configuration
- Every threshold lives in `backend/app/calculations/constants.py` as an editable default, also served at `GET /api/compliance/parameters`.
- `UCO_DB_PATH` (optional): SQLite file path; default `backend/uco_ulo.db` (gitignored).
- No secrets or API keys are used.

## Testing
```bash
pip install -r backend/requirements.txt ruff
ruff check .
pytest -q          # 35 tests; run from the repo root or from backend/
cd frontend && npm ci && npm run build
```
CI (`.github/workflows/ci.yml`) runs the same three steps.

## Limitations and known issues
- Mock data only; no authentication, audit users, PDF/Excel reports, route planning, IoT/photo evidence, or portal/RUCO ingestion (no public API found). See the end of `docs/PLATFORM_REVIEW.md`.
- Environmental Compensation INR/t is not captured (`EC_INR_PER_TONNE` is None until confirmed), so the certificate price band is inactive.
- The ledger is tamper-*evident* on one node only; anchor the head hash externally for stronger guarantees.
- Values marked VERIFY or PLACEHOLDER in `constants.py` must be reconciled with the official source before real use.

## Related repositories
- [saf-monitoring-system](https://github.com/herrrickshaw/saf-monitoring-system): same stack, SAF supply-chain monitoring.

## Licence
No licence file yet: all rights reserved.
