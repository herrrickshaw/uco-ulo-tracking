def test_dashboard(client):
    b = client.get("/api/dashboard/summary").json()
    assert b["uco_collected_tonnes"] > 0 and b["ulo_collected_tonnes"] > 0
    assert b["integrity_flags_high"] > 0


def test_seeded_lists(client):
    assert len(client.get("/api/generators").json()) == 8
    assert len(client.get("/api/generators", params={"material": "ULO"}).json()) == 3
    assert len(client.get("/api/lots").json()) == 12
    assert len(client.get("/api/batches").json()) == 12


def test_all_planted_anomalies_detected(client):
    checks = {f["check"] for f in client.get("/api/compliance/integrity").json()}
    assert {"suspiciously_fresh_uco", "generator_over_capacity", "collector_registration", "duplicate_manifest",
            "pcb_hazard_segregate", "mass_balance", "implausible_yield", "dispatch_exceeds_output"} <= checks


def test_epr_one_compliant_one_short(client):
    by = {r["producer"]: r for r in client.get("/api/compliance/epr").json()}
    assert by["Meridian Lubricants"]["compliant"] is True and not by["Meridian Lubricants"]["over_purchased"]
    assert by["Coastal Base Oils"]["compliant"] is False
    assert by["Coastal Base Oils"]["target_pct"] == 20 and by["Coastal Base Oils"]["basis_fy"] == "2024-25"


def test_certificate_ledger_generated_transferred_available(client):
    r = client.get("/api/compliance/epr/certificates").json()
    rb = next(x for x in r if x["recycler"] == "ReBase Re-refinery")
    assert rb["generated_mt"] > 0 and abs(rb["generated_mt"] - rb["transferred_mt"] - rb["available_mt"]) < 1e-6
    assert rb["available_mt"] > 0


def test_transfer_rules_enforced(client):
    prods = {p["producer"]: p for p in client.get("/api/compliance/epr").json()}
    pid = next(p["id"] for p in client.get("/api/compliance/epr").json()) if False else None
    from sqlalchemy import text  # noqa: F401  (ids resolved via direct lookup below)
    recyclers = [c for c in client.get("/api/collectors").json() if c["role"] == "recycler"]
    non_recycler = next(c for c in client.get("/api/collectors").json() if c["role"] == "aggregator")
    base = {"producer_id": 1, "certificate_fy": 2026, "tonnes": 0.1, "purchased_on": "2026-10-01"}
    assert client.post("/api/compliance/epr/purchases", json={**base, "recycler_id": non_recycler["id"]}).status_code == 400
    assert client.post("/api/compliance/epr/purchases", json={**base, "recycler_id": recyclers[0]["id"], "certificate_fy": 2022}).status_code == 400   # expired
    assert client.post("/api/compliance/epr/purchases", json={**base, "recycler_id": recyclers[0]["id"], "tonnes": 1e9}).status_code == 400   # > available
    assert prods


def test_shipment_flags_detected(client):
    checks = {f["check"] for f in client.get("/api/compliance/integrity").json()}
    assert {"vehicle_not_in_nhwts", "vehicle_no_gps", "transit_variance", "ca1_has_storage",
            "ca1_container_too_large", "ca1_out_of_radius"} <= checks


def test_returns_status(client):
    rows = client.get("/api/compliance/returns", params={"as_of": "2026-10-20"}).json()
    by = {(r["entity"], r["period"]): r["status"] for r in rows}
    assert by[("RoadRunner Used Oil", "Annual FY2024-25")] == "overdue"
    assert by[("RoadRunner Used Oil", "Q1 FY2026-27")] == "filed_late"
    assert by[("Enviro ULO Aggregation", "Annual FY2025-26")] == "due"       # extended to 30 Nov 2026


def test_ledger_intact_and_covers_events(client):
    led = client.get("/api/compliance/ledger").json()
    assert led["intact"] and led["entries"] > 60 and len(led["head_hash"]) == 64
    assert client.get("/api/dashboard/summary").json()["ledger_intact"] is True


def test_ghg_and_recycler_supply(client):
    assert all(r["tco2e_saved"] > 0 for r in client.get("/api/compliance/ghg").json())
    assert client.get("/api/compliance/epr/recycler-supply").json()[0]["end_product_tonnes"] > 0


def test_create_collection_validates_material(client):
    gid = client.get("/api/generators", params={"material": "ULO"}).json()[0]["id"]
    cid = client.get("/api/collectors").json()[0]["id"]
    r = client.post("/api/collections", json={"manifest_no": "T1", "generator_id": gid, "collector_id": cid,
                                              "material": "UCO", "collected_on": "2026-10-01", "quantity_litres": 100})
    assert r.status_code == 400


def test_batch_product_must_match_material(client):
    lot = next(l for l in client.get("/api/lots").json() if l["material"] == "ULO")
    pid = next(c for c in client.get("/api/collectors").json() if c["role"] == "recycler")["id"]
    r = client.post("/api/batches", json={"batch_code": "X", "lot_id": lot["id"], "processor_id": pid,
                                          "processed_on": "2026-10-01", "product": "biodiesel", "input_kg": 1, "output_kg": 1})
    assert r.status_code == 400
