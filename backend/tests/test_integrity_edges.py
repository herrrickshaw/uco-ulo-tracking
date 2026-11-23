"""Boundary behaviour of the pure integrity/quality checks (stand-in rows, no database)."""
from datetime import date
from types import SimpleNamespace as NS

import pytest

from app.calculations import constants as c
from app.calculations.integrity import run_checks
from app.calculations.quality import registration_valid, uco_quality_flags, ulo_quality_flags


def collection(material="UCO", tpc=20.0, **kw):
    gen = NS(name="G", material=material, monthly_purchase_litres=1_000_000.0)
    base = dict(manifest_no="M1", material=material, tpc_pct=tpc, ffa_pct=2.0, water_pct=0.0, pcb_ppm=0.0, chlorine_ppm=0.0,
                quantity_litres=10.0, collected_on=date(2026, 1, 15), generator_id=1, generator=gen,
                collector=NS(name="C", registration_valid_until=date(2030, 1, 1)))
    base.update(kw)
    return NS(**base)


def shipment(material="ULO", **kw):
    sender = NS(name="S", ca_level=None, has_storage=False)
    base = dict(manifest_no="F1", material=material, vehicle_no="V", nhwts_registered=True, gps_tracked=True, spcb_intimated=True,
                receiver=NS(name="R", registration_valid_until=date(2030, 1, 1)), dispatched_on=date(2026, 1, 1),
                dispatched_kg=1000.0, received_kg=1000.0, sender=sender, max_container_l=200.0, distance_km=10.0)
    base.update(kw)
    return NS(**base)


def checks(flags):
    return [(f["check"], f["severity"]) for f in flags]


# ------------------------------------------------------------------ quality thresholds
def test_uco_tpc_thresholds():
    assert uco_quality_flags(None) == ["tpc_missing"]
    assert uco_quality_flags(c.UCO_SUSPICIOUSLY_FRESH_TPC_PCT) == []                # exactly at the limit is not 'fresh'
    assert uco_quality_flags(c.UCO_SUSPICIOUSLY_FRESH_TPC_PCT - 0.1) == ["suspiciously_fresh"]
    assert uco_quality_flags(0.0) == ["suspiciously_fresh"]                         # 0 is a reading, not 'missing'


def test_ulo_thresholds_are_exclusive_except_pcb():
    assert ulo_quality_flags(c.ULO_MAX_WATER_PCT, 0, c.ULO_MAX_CHLORINE_PPM) == []
    assert ulo_quality_flags(c.ULO_MAX_WATER_PCT + 0.1, None, None) == ["high_water"]
    assert ulo_quality_flags(None, c.ULO_PCB_HAZARD_PPM, None) == ["pcb_hazard_segregate"]       # >= for PCB
    assert ulo_quality_flags(None, c.ULO_PCB_HAZARD_PPM - 0.1, None) == []
    assert ulo_quality_flags(None, None, c.ULO_MAX_CHLORINE_PPM + 1) == ["high_chlorine"]
    assert ulo_quality_flags(99, 99, 99999) == ["high_water", "pcb_hazard_segregate", "high_chlorine"]


def test_registration_valid_on_the_expiry_day():
    d = date(2026, 3, 31)
    assert registration_valid(d, d) is True and registration_valid(d, date(2026, 4, 1)) is False
    assert registration_valid(None, d) is False


# ------------------------------------------------------------------ collection checks
def test_missing_tpc_is_a_medium_flag_only_for_uco():
    assert checks(run_checks([collection(tpc=None)], [], [], [])) == [("tpc_missing", "medium")]
    assert run_checks([collection(material="ULO", tpc=None)], [], [], []) == []


def test_ulo_flag_severities():
    flags = run_checks([collection("ULO", water_pct=9.0, pcb_ppm=80.0, chlorine_ppm=5000.0)], [], [], [])
    assert dict(checks(flags)) == {"high_water": "medium", "pcb_hazard_segregate": "high", "high_chlorine": "medium"}


# ------------------------------------------------------------------ shipment checks
def test_ulo_transport_flags_and_uco_exemption():
    bad = dict(nhwts_registered=False, gps_tracked=False, spcb_intimated=False)
    got = dict(checks(run_checks([], [], [], [], [shipment("ULO", **bad)])))
    assert got == {"vehicle_not_in_nhwts": "high", "vehicle_no_gps": "high", "spcb_not_intimated": "medium"}
    assert run_checks([], [], [], [], [shipment("UCO", **bad)]) == []              # transport rules are ULO-only


def test_transit_variance_is_strictly_above_tolerance():
    tol = c.TRANSIT_LOSS_TOLERANCE_PCT
    at = shipment(received_kg=1000.0 * (1 - tol / 100))
    over = shipment(received_kg=1000.0 * (1 - tol / 100) - 1)
    gain = shipment(received_kg=1000.0 * (1 + tol / 100) + 1)                       # absolute variance: over-delivery counts too
    assert run_checks([], [], [], [], [at]) == []
    assert [f["check"] for f in run_checks([], [], [], [], [over])] == ["transit_variance"]
    assert [f["check"] for f in run_checks([], [], [], [], [gain])] == ["transit_variance"]
    assert run_checks([], [], [], [], [shipment(received_kg=None)]) == []
    assert run_checks([], [], [], [], [shipment(dispatched_kg=0.0, received_kg=5.0)]) == []   # no division by zero


def test_receiver_registration_checked_on_dispatch_date():
    ok = shipment(receiver=NS(name="R", registration_valid_until=date(2026, 1, 1)))
    late = shipment(receiver=NS(name="R", registration_valid_until=date(2025, 12, 31)))
    assert run_checks([], [], [], [], [ok]) == []
    assert [f["check"] for f in run_checks([], [], [], [], [late])] == ["receiver_registration"]


@pytest.mark.parametrize("km,expected", [
    (c.CA1_RADIUS_KM, []),                                                          # exactly 75: allowed
    (c.CA1_RADIUS_KM + 1, [("ca1_out_of_radius", "medium")]),
    (c.CA1_RADIUS_NO_RECYCLER_KM, [("ca1_out_of_radius", "medium")]),               # exactly 150: still only 'medium'
    (c.CA1_RADIUS_NO_RECYCLER_KM + 1, [("ca1_out_of_radius", "high")]),
])
def test_ca1_haul_radius_severity(km, expected):
    s = shipment(sender=NS(name="S", ca_level=1, has_storage=False), distance_km=km)
    assert checks(run_checks([], [], [], [], [s])) == expected


def test_ca1_storage_and_container_rules():
    s = shipment(sender=NS(name="S", ca_level=1, has_storage=True), max_container_l=c.CA1_MAX_CONTAINER_L + 1)
    assert dict(checks(run_checks([], [], [], [], [s]))) == {"ca1_has_storage": "high", "ca1_container_too_large": "high"}
    at_limit = shipment(sender=NS(name="S", ca_level=1, has_storage=False), max_container_l=c.CA1_MAX_CONTAINER_L)
    assert run_checks([], [], [], [], [at_limit]) == []
    ca2 = shipment(sender=NS(name="S", ca_level=2, has_storage=True), max_container_l=5000.0, distance_km=999.0)
    assert run_checks([], [], [], [], [ca2]) == []                                  # CA-2 rules differ; UCO senders are exempt too
