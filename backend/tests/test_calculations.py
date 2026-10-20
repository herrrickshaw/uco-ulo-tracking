from app.calculations.epr import obligation, target_pct
from app.calculations.ghg import ghg_savings
from app.calculations.mass_balance import lot_balance, yield_ok
from app.calculations.quality import uco_quality_flags, ulo_quality_flags


def test_fresh_uco_flagged():
    assert "suspiciously_fresh" in uco_quality_flags(3.0)
    assert uco_quality_flags(25.0) == []
    assert uco_quality_flags(None) == ["tpc_missing"]


def test_ulo_flags():
    assert set(ulo_quality_flags(9.0, 120.0, 2000.0)) == {"high_water", "pcb_hazard_segregate", "high_chlorine"}
    assert ulo_quality_flags(1.0, 2.0, 100.0) == []


def test_mass_balance_tolerance():
    assert lot_balance(1000, 1015)["balanced"] is True
    assert lot_balance(1000, 1100)["balanced"] is False


def test_yield_ranges():
    assert yield_ok("biodiesel", 1000, 880)
    assert not yield_ok("biodiesel", 1000, 990)
    assert not yield_ok("base_oil", 0, 0)


def test_epr_target_endpoints_and_obligation():
    assert target_pct(2024) == 5.0 and target_pct(2030) == 50.0 and target_pct(2035) == 50.0 and target_pct(2020) == 0.0
    o = obligation(1000, 2025, 100)
    assert o["required_tonnes"] == 125.0 and o["shortfall_tonnes"] == 25.0 and not o["compliant"]


def test_ghg_savings():
    g = ghg_savings("biodiesel", 1000)
    assert g["savings_pct"] == 78.7 and g["tco2e_saved"] > 0
    assert ghg_savings("base_oil", 1000) is None
