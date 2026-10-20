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
    assert by["Meridian Lubricants"]["compliant"] is True
    assert by["Coastal Base Oils"]["compliant"] is False


def test_ghg_and_recycler_supply(client):
    assert all(r["tco2e_saved"] > 0 for r in client.get("/api/compliance/ghg").json())
    assert client.get("/api/compliance/epr/recycler-supply").json()[0]["recycled_tonnes"] > 0


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
