"""Write endpoints, ledger tamper-evidence and EPR transfer rules against a private, freshly seeded
database per test (the shared session-scoped `client` fixture is read-only by convention)."""
from datetime import date, timedelta

import pytest

from app.calculations import constants as c

# NOTE: nothing that imports app.db / app.models may be imported at module level here. app.db builds its
# engine from UCO_DB_PATH at import time, and the session `client` fixture sets that variable first;
# importing earlier would silently point every test at the developer's backend/uco_ulo.db.


class Fresh:
    def __init__(self, client, Session):
        self.client, self.Session = client, Session

    def get(self, *a, **k):
        return self.client.get(*a, **k)

    def post(self, *a, **k):
        return self.client.post(*a, **k)

    def ledger(self):
        return self.client.get("/api/compliance/ledger").json()


@pytest.fixture
def fresh(client, tmp_path):
    # `client` (session fixture) guarantees app.db was imported with the test DB path first.
    from fastapi.testclient import TestClient
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.db import Base, get_db
    from app.main import app
    from app.seed.mock_data import seed_if_empty

    engine = create_engine(f"sqlite:///{tmp_path / 'fresh.db'}", connect_args={"check_same_thread": False})
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(bind=engine)
    with Session() as s:
        seed_if_empty(s)
        s.commit()

    def override():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    try:
        yield Fresh(TestClient(app), Session)
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def collection_payload(f, material="UCO", **kw):
    gen = next(g for g in f.get("/api/generators", params={"material": material}).json())
    col = next(x for x in f.get("/api/collectors").json() if x["material"] == material and x["role"] == "collector")
    p = {"manifest_no": "NEW-1", "generator_id": gen["id"], "collector_id": col["id"], "material": material,
         "collected_on": "2026-10-01", "quantity_litres": 100.0, "tpc_pct": 20.0, "ffa_pct": 3.0}
    p.update(kw)
    return p


# ------------------------------------------------------------------ list filters and ordering
def test_collections_listing_filter_and_order(fresh):
    allc = fresh.get("/api/collections").json()
    uco = fresh.get("/api/collections", params={"material": "UCO"}).json()
    ulo = fresh.get("/api/collections", params={"material": "ULO"}).json()
    assert len(uco) + len(ulo) == len(allc) and uco and ulo
    assert {x["material"] for x in uco} == {"UCO"}
    dates = [x["collected_on"] for x in allc]
    assert dates == sorted(dates, reverse=True)                              # newest first


def test_collectors_dispatches_and_batches_lists(fresh):
    assert len(fresh.get("/api/collectors").json()) == 8
    assert len(fresh.get("/api/dispatches").json()) == 12
    b = fresh.get("/api/batches").json()
    assert [x["processed_on"] for x in b] == sorted((x["processed_on"] for x in b), reverse=True)
    lots = fresh.get("/api/lots").json()
    assert [x["formed_on"] for x in lots] == sorted((x["formed_on"] for x in lots), reverse=True)
    assert all({"n_collections", "aggregator"} <= set(x) for x in lots)


# ------------------------------------------------------------------ POST /collections
def test_create_collection_persists_and_extends_the_ledger(fresh):
    before = fresh.ledger()["entries"]
    r = fresh.post("/api/collections", json=collection_payload(fresh))
    assert r.status_code == 200 and r.json()["manifest_no"] == "NEW-1" and r.json()["id"]
    after = fresh.ledger()
    assert after["entries"] == before + 1 and after["intact"] is True
    assert any(x["manifest_no"] == "NEW-1" for x in fresh.get("/api/collections").json())


def test_create_collection_rejections_leave_no_trace(fresh):
    before = fresh.ledger()["entries"]
    n = len(fresh.get("/api/collections").json())
    assert fresh.post("/api/collections", json=collection_payload(fresh, generator_id=9999)).status_code == 404
    assert fresh.post("/api/collections", json=collection_payload(fresh, collector_id=9999)).status_code == 404
    bad = fresh.post("/api/collections", json=collection_payload(fresh, material="UCO") | {"material": "ULO"})
    assert bad.status_code == 400 and "Generator handles UCO, not ULO" in bad.json()["detail"]
    assert fresh.post("/api/collections", json={"manifest_no": "x"}).status_code == 422
    assert fresh.ledger()["entries"] == before and len(fresh.get("/api/collections").json()) == n


# ------------------------------------------------------------------ POST /batches, /dispatches, /shipments
def test_create_batch_rules(fresh):
    lots = fresh.get("/api/lots").json()
    uco_lot = next(x for x in lots if x["material"] == "UCO")
    colls = {x["name"]: x for x in fresh.get("/api/collectors").json()}
    base = {"batch_code": "B-NEW", "lot_id": uco_lot["id"], "processor_id": colls["Deccan Biofuels"]["id"],
            "processed_on": "2026-10-05", "product": "biodiesel", "input_kg": 1000.0, "output_kg": 880.0}
    assert fresh.post("/api/batches", json=base | {"lot_id": 9999}).status_code == 404
    r = fresh.post("/api/batches", json=base | {"product": "base_oil"})
    assert r.status_code == 400 and "base_oil is not a product of UCO" in r.json()["detail"]
    before = fresh.ledger()["entries"]
    ok = fresh.post("/api/batches", json=base)
    assert ok.status_code == 200 and ok.json()["batch_code"] == "B-NEW"
    assert fresh.ledger()["entries"] == before + 1
    assert any(x["batch_code"] == "B-NEW" for x in fresh.get("/api/batches").json())


def test_create_dispatch_rules(fresh):
    batch = fresh.get("/api/batches").json()[0]
    assert fresh.post("/api/dispatches", json={"batch_id": 9999, "buyer": "x", "dispatched_on": "2026-10-10", "quantity_kg": 1}).status_code == 404
    n = len(fresh.get("/api/dispatches").json())
    r = fresh.post("/api/dispatches", json={"batch_id": batch["id"], "buyer": "Buyer", "dispatched_on": "2026-10-10", "quantity_kg": 5.0})
    assert r.status_code == 200 and len(fresh.get("/api/dispatches").json()) == n + 1
    assert fresh.ledger()["intact"] is True


def test_create_shipment_rules_and_ordering(fresh):
    cols = fresh.get("/api/collectors").json()
    a, b = cols[0]["id"], cols[1]["id"]
    base = {"manifest_no": "F-NEW", "material": "UCO", "sender_id": a, "receiver_id": b, "vehicle_no": "KA01-AA-0001",
            "dispatched_on": "2030-01-01", "dispatched_kg": 100.0}
    assert fresh.post("/api/shipments", json=base | {"sender_id": 9999}).status_code == 404
    assert fresh.post("/api/shipments", json=base | {"receiver_id": 9999}).status_code == 404
    r = fresh.post("/api/shipments", json=base)
    assert r.status_code == 200 and r.json()["gps_tracked"] is True and r.json()["max_container_l"] == 200.0   # defaults
    ships = fresh.get("/api/shipments").json()
    assert ships[0]["manifest_no"] == "F-NEW"                                  # newest dispatch first
    assert [s["dispatched_on"] for s in ships] == sorted((s["dispatched_on"] for s in ships), reverse=True)


# ------------------------------------------------------------------ ledger tamper evidence via /compliance/integrity
def tamper(f, fn):
    with f.Session() as s:
        fn(s)
        s.commit()


def test_editing_a_logged_row_is_detected(fresh):
    from app.models import Collection
    fresh.post("/api/collections", json=collection_payload(fresh))
    assert fresh.ledger()["intact"] is True
    tamper(fresh, lambda s: setattr(s.query(Collection).filter_by(manifest_no="NEW-1").one(), "quantity_litres", 999.0))
    led = fresh.ledger()
    assert led["intact"] is False and led["problems"][0]["problem"].endswith("modified after logging")
    flags = fresh.get("/api/compliance/integrity").json()
    changed = [f for f in flags if f["check"] == "ledger_record_changed"]
    assert len(changed) == 1 and changed[0]["severity"] == "high"
    assert all(f["severity"] == "high" for f in fresh.get("/api/compliance/integrity", params={"severity": "high"}).json())
    assert {f["severity"] for f in fresh.get("/api/compliance/integrity", params={"severity": "medium"}).json()} <= {"medium"}


def test_deleting_a_logged_row_is_detected(fresh):
    from app.models import Collection
    fresh.post("/api/collections", json=collection_payload(fresh))
    tamper(fresh, lambda s: s.delete(s.query(Collection).filter_by(manifest_no="NEW-1").one()))
    problems = fresh.ledger()["problems"]
    assert problems and problems[0]["problem"].endswith("deleted after logging")


def test_breaking_the_hash_chain_is_detected(fresh):
    from app.models import LedgerEntry
    for i in (1, 2):
        fresh.post("/api/collections", json=collection_payload(fresh, manifest_no=f"N{i}"))
    tamper(fresh, lambda s: setattr(s.query(LedgerEntry).order_by(LedgerEntry.id).first(), "payload", "{}"))
    probs = fresh.ledger()["problems"]
    assert any(p["problem"] == "chain_broken" for p in probs)
    kinds = [f["check"] for f in fresh.get("/api/compliance/integrity").json()]
    assert "ledger_chain_broken" in kinds


# ------------------------------------------------------------------ EPR transfers
def recycler_id(f):
    return next(x["id"] for x in f.get("/api/collectors").json() if x["role"] == "recycler")


def purchase(f, **kw):
    p = {"producer_id": 1, "recycler_id": recycler_id(f), "certificate_fy": 2026, "tonnes": 0.01, "purchased_on": "2026-10-20"}
    p.update(kw)
    return f.post("/api/compliance/epr/purchases", json=p)


def test_transfer_success_updates_certificate_ledger(fresh):
    before = next(x for x in fresh.get("/api/compliance/epr/certificates").json() if x["recycler"] == "ReBase Re-refinery")
    bought_before = fresh.get("/api/compliance/epr").json()[0]["certificates_tonnes"]
    r = purchase(fresh, tonnes=0.5)
    assert r.status_code == 200 and r.json()["certificates_tonnes"] == round(bought_before + 0.5, 2) and r.json()["id"]
    after = next(x for x in fresh.get("/api/compliance/epr/certificates").json() if x["recycler"] == "ReBase Re-refinery")
    assert after["transferred_mt"] == pytest.approx(before["transferred_mt"] + 0.5)
    assert after["available_mt"] == pytest.approx(before["available_mt"] - 0.5)


def test_transfer_unknown_parties_and_recycler_only(fresh):
    assert purchase(fresh, producer_id=9999).status_code == 404
    assert purchase(fresh, recycler_id=9999).status_code == 404
    agg = next(x["id"] for x in fresh.get("/api/collectors").json() if x["role"] == "aggregator")
    r = purchase(fresh, recycler_id=agg)
    assert r.status_code == 400 and "only be bought from a registered recycler" in r.json()["detail"]


def test_certificate_expiry_boundary_is_inclusive(fresh):
    expiry = date(2029, 3, 31)                                                 # FY2026 certificates: 31 Mar 2029
    assert purchase(fresh, purchased_on=expiry.isoformat()).status_code == 200
    late = purchase(fresh, purchased_on=(expiry + timedelta(days=1)).isoformat())
    assert late.status_code == 400 and "expired on 2029-03-31" in late.json()["detail"]


def test_transfer_cannot_exceed_available_certificates(fresh):
    avail = next(x for x in fresh.get("/api/compliance/epr/certificates").json() if x["recycler"] == "ReBase Re-refinery")["available_mt"]
    assert purchase(fresh, tonnes=avail + 1).status_code == 400
    assert "only" in purchase(fresh, tonnes=avail + 1).json()["detail"]


def test_purchase_cap_is_liability_plus_ten_percent(fresh):
    """Give the recycler plenty of certificates so only the producer's purchase cap can bind."""
    from app.models import EPRCertificate, ProcessingBatch
    rid = recycler_id(fresh)

    def add_big_certificate(s):
        spare = s.query(ProcessingBatch).filter(~ProcessingBatch.id.in_(s.query(EPRCertificate.batch_id))).first()
        s.add(EPRCertificate(batch_id=spare.id, recycler_id=rid, fy_start_year=2026, route="re_refining",
                             qp_tonnes=1.0, cf=1.5, wp=1.0, tonnes=100_000.0))
    tamper(fresh, add_big_certificate)
    epr = fresh.get("/api/compliance/epr").json()[0]
    room = round(epr["max_purchasable_tonnes"] - epr["certificates_tonnes"], 2)
    assert room > 0
    over = purchase(fresh, tonnes=room + 0.02)
    assert over.status_code == 400 and f"purchase cap of {epr['max_purchasable_tonnes']} t" in over.json()["detail"]
    assert purchase(fresh, tonnes=room).status_code == 200                       # exactly at the cap is allowed
    assert purchase(fresh, tonnes=0.02).status_code == 400                       # nothing left above the cap


def test_price_band_enforced_only_when_ec_rate_is_set(fresh, monkeypatch):
    assert purchase(fresh, price_inr_per_tonne=1.0).status_code == 200        # no EC rate -> no band
    monkeypatch.setattr(c, "EC_INR_PER_TONNE", 1000.0)                        # band = 300..1000 INR/t
    assert purchase(fresh, price_inr_per_tonne=299.0).status_code == 400
    assert purchase(fresh, price_inr_per_tonne=1001.0).status_code == 400
    assert purchase(fresh, price_inr_per_tonne=300.0).status_code == 200      # inclusive lower edge
    assert purchase(fresh, price_inr_per_tonne=1000.0).status_code == 200     # inclusive upper edge
    assert purchase(fresh).status_code == 200                                 # unpriced transfer allowed


# ------------------------------------------------------------------ read-only compliance endpoints
def test_recycler_supply_sums_by_recycler_and_route(fresh):
    rows = fresh.get("/api/compliance/epr/recycler-supply").json()
    assert rows and all({"recycler", "route", "end_product_tonnes"} == set(r) for r in rows)
    assert {r["recycler"] for r in rows} == {"ReBase Re-refinery"} and rows[0]["route"] == "re_refining"
    gens = {r["recycler"]: r["generated_mt"] for r in fresh.get("/api/compliance/epr/certificates").json()}
    assert gens["ReBase Re-refinery"] > 0 and rows[0]["end_product_tonnes"] > 0


def test_ghg_lists_uco_batches_only(fresh):
    rows = fresh.get("/api/compliance/ghg").json()
    assert rows and all(r["product"] in {"biodiesel", "hefa_feedstock"} for r in rows)
    assert all(r["batch"].startswith("B-UCO-") for r in rows)


def test_parameters_exposes_every_uppercase_constant(fresh):
    p = fresh.get("/api/compliance/parameters").json()
    assert p["FSSAI_TPC_LIMIT_PCT"] == 25.0 and p["PURCHASE_CAP_MARGIN_PCT"] == 10.0
    assert all(k.isupper() for k in p)


def test_returns_default_as_of_is_today(fresh):
    default = fresh.get("/api/compliance/returns").json()
    explicit = fresh.get("/api/compliance/returns", params={"as_of": date.today().isoformat()}).json()
    assert default == explicit and [r["due_on"] for r in default] == sorted(r["due_on"] for r in default)


def test_seeding_is_idempotent(fresh):
    from app.models import Collection, Generator
    from app.seed.mock_data import seed_if_empty
    with fresh.Session() as s:
        n_gen, n_col = s.query(Generator).count(), s.query(Collection).count()
        seed_if_empty(s)
        s.commit()
        assert (s.query(Generator).count(), s.query(Collection).count()) == (n_gen, n_col) and n_gen == 8
