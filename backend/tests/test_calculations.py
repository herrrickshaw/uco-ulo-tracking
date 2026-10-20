from datetime import date

from app.calculations.epr import certificate_expiry, certificate_tonnes, fy_start_year, obligation, price_band, target_pct
from app.calculations.returns import annual_due, quarter_due
from app.calculations.returns import status as return_status
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


def test_epr_schedule_matches_cpcb_faq():
    assert [target_pct(y) for y in range(2024, 2030)] == [5, 10, 20, 20, 40, 40]
    assert target_pct(2030) == 50 and target_pct(2035) == 50 and target_pct(2023) == 0
    assert target_pct(2026, "used_oil_importer") == 100


def test_epr_obligation_uses_y_minus_2_base_and_purchase_cap():
    o = obligation(1000, 2026, 150)          # 20% of 1000 = 200 required
    assert o["required_tonnes"] == 200 and o["shortfall_tonnes"] == 50 and not o["compliant"]
    assert o["basis_fy"] == "2024-25" and o["max_purchasable_tonnes"] == 220
    assert obligation(1000, 2026, 230)["over_purchased"] is True
    assert obligation(500, 2026, 500, "used_oil_importer")["basis_fy"] == "2025-26"


def test_certificate_formula_and_expiry():
    assert certificate_tonnes(10, 1.5, "re_refining") == 15.0
    assert certificate_tonnes(10, 1.5, "co_processing") == 3.75
    assert certificate_expiry(2025) == date(2028, 3, 31)
    assert fy_start_year(date(2026, 3, 31)) == 2025 and fy_start_year(date(2026, 4, 1)) == 2026
    assert price_band(None) is None and price_band(1000) == (300.0, 1000.0)


def test_return_due_dates():
    assert quarter_due(2026, 1) == date(2026, 7, 31) and quarter_due(2026, 2) == date(2026, 10, 31)
    assert quarter_due(2026, 3) == date(2027, 1, 31) and quarter_due(2026, 4) == date(2027, 4, 30)
    assert annual_due(2024) == date(2025, 6, 30)
    assert annual_due(2025, "Annual FY2025-26") == date(2026, 11, 30)       # portal extension notice
    assert return_status(date(2026, 7, 31), None, date(2026, 8, 1)) == "overdue"
    assert return_status(date(2026, 7, 31), date(2026, 8, 5), date(2026, 9, 1)) == "filed_late"


def test_ledger_detects_edit_after_logging():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from app.calculations import ledger
    from app.db import Base
    from app.models import Collection, Collector, Generator

    eng = create_engine("sqlite://")
    Base.metadata.create_all(eng)
    db = sessionmaker(bind=eng)()
    g = Generator(name="g", material="UCO", sector="x", state="x", monthly_purchase_litres=100)
    cl = Collector(name="c", role="collector", material="UCO")
    db.add_all([g, cl]); db.flush()
    col = Collection(manifest_no="A", generator_id=g.id, collector_id=cl.id, material="UCO", collected_on=date(2026, 1, 1), quantity_litres=50)
    db.add(col); db.commit()
    ledger.append(db, "collection", col)
    assert ledger.verify(db)["intact"]
    col.quantity_litres = 500; db.commit()                                   # silent edit of the source row
    assert "modified after logging" in ledger.verify(db)["problems"][0]["problem"]
    col.quantity_litres = 50; db.commit()
    assert ledger.verify(db)["intact"]
    e = db.query(ledger.LedgerEntry).first(); e.payload = e.payload.replace("50", "51"); db.commit()   # edit the log itself
    assert any(p["problem"] == "chain_broken" for p in ledger.verify(db)["problems"])


def test_ghg_savings():
    g = ghg_savings("biodiesel", 1000)
    assert g["savings_pct"] == 78.7 and g["tco2e_saved"] > 0
    assert ghg_savings("base_oil", 1000) is None
