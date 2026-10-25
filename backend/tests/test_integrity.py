"""Unit tests for calculations/integrity.run_checks on synthetic in-memory rows
(SimpleNamespace stand-ins for the ORM objects -- no database)."""
from datetime import date
from types import SimpleNamespace as NS

import pytest

from app.calculations.integrity import run_checks

VALID = date(2030, 1, 1)


def _gen(gid=1, material="UCO", monthly=1000.0):
    return NS(id=gid, name=f"gen{gid}", material=material, monthly_purchase_litres=monthly)


def _collector(valid_until=VALID):
    return NS(name="collector", registration_valid_until=valid_until)


def _col(manifest, gen, litres, *, on=date(2026, 1, 10), tpc=20.0, material=None, collector=None,
         water=None, pcb=None, chlorine=None):
    return NS(manifest_no=manifest, generator=gen, generator_id=gen.id, quantity_litres=litres,
              collected_on=on, material=material or gen.material, tpc_pct=tpc, ffa_pct=None,
              collector=collector or _collector(), water_pct=water, pcb_ppm=pcb, chlorine_ppm=chlorine)


def _checks(flags):
    return sorted(f["check"] for f in flags)


def test_clean_data_raises_no_flags():
    g = _gen()
    cols = [_col("M1", g, 300.0), _col("M2", g, 200.0)]          # 500 L <= 0.6 x 1000
    lot = NS(lot_code="L1", material="UCO", collections=cols, batches=[])
    batch = NS(batch_code="B1", lot=lot, product="biodiesel", input_kg=400.0, output_kg=360.0,
               unfit_declaration_ref=None, dispatches=[NS(quantity_kg=360.0)])
    lot.batches = [batch]
    assert run_checks(cols, [lot], [batch], []) == []


def test_empty_inputs():
    assert run_checks([], [], [], []) == []


def test_duplicate_manifest_and_expired_registration_and_fresh_oil():
    g = _gen()
    cols = [_col("DUP", g, 10.0), _col("DUP", g, 10.0, tpc=3.0, collector=_collector(date(2025, 12, 31)))]
    flags = _checks(run_checks(cols, [], [], []))
    assert flags.count("duplicate_manifest") == 2
    assert "collector_registration" in flags and "suspiciously_fresh_uco" in flags


def test_generator_over_capacity_uses_60pct_recoverable_per_month():
    g = _gen(monthly=1000.0)                                     # cap 600 L / month
    jan = [_col("A", g, 400.0), _col("B", g, 201.0)]             # 601 L -> flag
    feb = [_col("C", g, 600.0, on=date(2026, 2, 3))]             # exactly cap -> ok
    flags = run_checks(jan + feb, [], [], [])
    over = [f for f in flags if f["check"] == "generator_over_capacity"]
    assert len(over) == 1 and over[0]["ref"] == "gen1 2026-01"


def test_lot_mass_balance_converts_litres_to_kg():
    g = _gen()
    cols = [_col("A", g, 500.0)]                                 # 500 L x 0.92 = 460 kg
    ok = NS(lot_code="OK", material="UCO", collections=cols, batches=[NS(input_kg=469.2)])   # +2 %
    bad = NS(lot_code="BAD", material="UCO", collections=cols, batches=[NS(input_kg=469.3)])
    flags = run_checks([], [ok, bad], [], [])
    assert [f["ref"] for f in flags if f["check"] == "mass_balance"] == ["lot BAD"]


def test_batch_product_mismatch_yield_declaration_and_dispatch():
    lot = NS(lot_code="L", material="ULO", collections=[], batches=[])
    wrong = NS(batch_code="W", lot=lot, product="biodiesel", input_kg=100.0, output_kg=90.0,
               unfit_declaration_ref=None, dispatches=[])
    high = NS(batch_code="H", lot=lot, product="base_oil", input_kg=100.0, output_kg=90.0,
              unfit_declaration_ref=None, dispatches=[])
    fuel = NS(batch_code="F", lot=lot, product="fuel_oil", input_kg=100.0, output_kg=80.0,
              unfit_declaration_ref="", dispatches=[NS(quantity_kg=81.7)])          # > 80 x 1.02
    flags = {(f["ref"], f["check"]) for f in run_checks([], [], [wrong, high, fuel], [])}
    assert ("batch W", "product_mismatch") in flags
    assert ("batch H", "implausible_yield") in flags                                # 0.90 > 0.85
    assert ("batch F", "coprocessing_without_declaration") in flags
    assert ("batch F", "dispatch_exceeds_output") in flags


def test_zero_input_batch_is_flagged_not_crash():
    """Prove-it: a batch recorded with input_kg = 0 (the API does not forbid it)
    made run_checks divide by zero, taking down the whole integrity report."""
    lot = NS(lot_code="L", material="UCO", collections=[], batches=[])
    b = NS(batch_code="Z", lot=lot, product="biodiesel", input_kg=0.0, output_kg=50.0,
           unfit_declaration_ref=None, dispatches=[])
    flags = run_checks([], [], [b], [])
    assert [f["check"] for f in flags] == ["implausible_yield"]


def _shipment(**kw):
    base = dict(manifest_no="S1", material="ULO", nhwts_registered=True, gps_tracked=True,
                spcb_intimated=True, receiver=_collector(), dispatched_on=date(2026, 1, 1),
                received_kg=1000.0, dispatched_kg=1000.0,
                sender=NS(name="ca", ca_level=2, has_storage=True), max_container_l=1000.0,
                distance_km=300.0, vehicle_no="KA01")
    base.update(kw)
    return NS(**base)


def test_clean_shipment_no_flags():
    assert run_checks([], [], [], [], [_shipment()]) == []


def test_ulo_shipment_transport_rules_and_transit_variance():
    sh = _shipment(nhwts_registered=False, gps_tracked=False, spcb_intimated=False,
                   received_kg=969.0)                                               # 3.1 % short
    assert _checks(run_checks([], [], [], [], [sh])) == [
        "spcb_not_intimated", "transit_variance", "vehicle_no_gps", "vehicle_not_in_nhwts"]
    assert run_checks([], [], [], [], [_shipment(received_kg=970.0)]) == []          # 3.0 % ok


@pytest.mark.parametrize("km,severity", [(75.0, None), (76.0, "medium"), (151.0, "high")])
def test_ca1_radius_rules(km, severity):
    sh = _shipment(sender=NS(name="ca1", ca_level=1, has_storage=False), max_container_l=200.0,
                   distance_km=km)
    flags = [f for f in run_checks([], [], [], [], [sh]) if f["check"] == "ca1_out_of_radius"]
    assert (flags[0]["severity"] if flags else None) == severity


def test_ca1_storage_and_container():
    sh = _shipment(sender=NS(name="ca1", ca_level=1, has_storage=True), max_container_l=201.0,
                   distance_km=10.0)
    assert _checks(run_checks([], [], [], [], [sh])) == ["ca1_container_too_large", "ca1_has_storage"]


def test_uco_shipment_skips_ulo_transport_rules():
    sh = _shipment(material="UCO", nhwts_registered=False, gps_tracked=False, spcb_intimated=False)
    assert run_checks([], [], [], [], [sh]) == []
