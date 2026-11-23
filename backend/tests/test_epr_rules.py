"""Pure EPR arithmetic: obligation targets, purchase cap tolerance, certificate expiry, price band."""
from datetime import date

from app.calculations import constants as c
from app.calculations.epr import basis_year, certificate_expiry, certificate_tonnes, fy_start_year, obligation, price_band, target_pct


def test_target_pct_by_year_and_basis():
    assert target_pct(2023) == 0.0                              # before the first obligation year
    assert target_pct(2024) == 5.0 and target_pct(2026) == 20.0 and target_pct(2029) == 40.0
    assert target_pct(2030) == 50.0 and target_pct(2045) == 50.0
    assert target_pct(2020, "used_oil_importer") == c.EPR_IMPORTER_PCT == 100.0     # importers ignore the schedule


def test_basis_year_lag_differs_for_importers():
    assert basis_year(2026) == 2024 and basis_year(2026, "used_oil_importer") == 2025


def test_obligation_arithmetic():
    ob = obligation(1000.0, 2026, 150.0)
    assert ob["required_tonnes"] == 200.0 and ob["shortfall_tonnes"] == 50.0 and ob["compliant"] is False
    assert ob["max_purchasable_tonnes"] == 220.0 and ob["basis_fy"] == "2024-25" and ob["target_pct"] == 20.0
    assert obligation(1000.0, 2026, 200.0)["compliant"] is True and obligation(1000.0, 2026, 200.0)["shortfall_tonnes"] == 0.0
    assert obligation(1000.0, 2026, 500.0)["shortfall_tonnes"] == 0.0           # surplus never goes negative
    assert obligation(1000.0, 2026, 0.0, leftover_tonnes=30.0)["max_purchasable_tonnes"] == 250.0


def test_purchase_cap_epsilon_is_one_nano_tonne():
    cap = 200.0 + 0.0 + 200.0 * c.PURCHASE_CAP_MARGIN_PCT / 100
    assert obligation(1000.0, 2026, cap)["over_purchased"] is False
    assert obligation(1000.0, 2026, cap + 1e-9)["over_purchased"] is False      # inside the tolerance
    assert obligation(1000.0, 2026, cap + 2e-9)["over_purchased"] is True


def test_certificate_tonnes_and_weightage():
    assert certificate_tonnes(10.0, 1.5, "re_refining") == 15.0
    assert certificate_tonnes(10.0, 1.5, "co_processing") == 3.75


def test_certificate_expiry_and_fy():
    assert certificate_expiry(2026) == date(2029, 3, 31)
    assert fy_start_year(date(2026, 3, 31)) == 2025 and fy_start_year(date(2026, 4, 1)) == 2026


def test_price_band(monkeypatch):
    assert price_band(None) is None
    assert price_band(1000.0) == (300.0, 1000.0)
    assert price_band(0.0) == (0.0, 0.0)
