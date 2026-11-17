"""Unit tests for the pure integrity checks, using lightweight stand-ins for ORM rows."""
from datetime import date
from types import SimpleNamespace as NS

from app.calculations.integrity import run_checks
from app.calculations.mass_balance import lot_balance, lot_totals, yield_ok


def _collection(manifest="M1", material="UCO", tpc=20.0, litres=100.0, valid_until=date(2030, 1, 1), gen_id=1, purchase=10_000.0):
    gen = NS(name="G", material=material, monthly_purchase_litres=purchase)
    col = NS(manifest_no=manifest, material=material, tpc_pct=tpc, ffa_pct=2.0, water_pct=0.0, pcb_ppm=0.0, chlorine_ppm=0.0,
             quantity_litres=litres, collected_on=date(2026, 1, 15), generator_id=gen_id, generator=gen,
             collector=NS(name="C", registration_valid_until=valid_until))
    return col


def _checks(flags):
    return [f["check"] for f in flags]


def test_clean_collection_has_no_flags():
    assert run_checks([_collection()], [], [], []) == []


def test_duplicate_manifest_and_expired_registration():
    cols = [_collection(valid_until=date(2020, 1, 1)), _collection()]
    kinds = _checks(run_checks(cols, [], [], []))
    assert kinds.count("duplicate_manifest") == 2
    assert "collector_registration" in kinds


def test_fresh_uco_flagged():
    assert "suspiciously_fresh_uco" in _checks(run_checks([_collection(tpc=1.0)], [], [], []))


def test_generator_over_capacity():
    flags = run_checks([_collection(litres=1_000_000.0)], [], [], [])
    assert "generator_over_capacity" in _checks(flags)


def test_lot_mass_balance_flag():
    col = NS(quantity_litres=100.0)
    lot = NS(material="UCO", lot_code="L1", collections=[col], batches=[NS(input_kg=1e6)])
    received, processed = lot_totals(lot)
    assert processed == 1e6 and received < processed
    assert "mass_balance" in _checks(run_checks([], [lot], [], []))


def test_lot_balance_and_yield_helpers():
    assert lot_balance(100, 50)["balanced"] and lot_balance(100, 50)["unprocessed_kg"] == 50
    assert not yield_ok("biodiesel", 0, 10)


def test_batch_product_mismatch():
    batch = NS(batch_code="B1", product="base_oil", input_kg=100, output_kg=80, unfit_declaration_ref="",
               lot=NS(material="UCO"), dispatches=[])
    assert "product_mismatch" in _checks(run_checks([], [], [batch], []))
