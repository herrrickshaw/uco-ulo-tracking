from datetime import date

from . import constants as c


def target_pct(fy_start_year: int, basis: str = "producer") -> float:
    if basis == "used_oil_importer":
        return c.EPR_IMPORTER_PCT
    if fy_start_year < min(c.EPR_PRODUCER_PCT):
        return 0.0
    if fy_start_year >= 2030:
        return c.EPR_PRODUCER_PCT_FROM_2030
    return c.EPR_PRODUCER_PCT[fy_start_year]


def basis_year(fy_start_year: int, basis: str = "producer") -> int:
    lag = c.EPR_IMPORTER_BASE_YEAR_LAG if basis == "used_oil_importer" else c.EPR_BASE_YEAR_LAG
    return fy_start_year - lag


def obligation(basis_tonnes: float, fy_start_year: int, certificates_tonnes: float, basis: str = "producer",
               leftover_tonnes: float = 0.0) -> dict:
    pct = target_pct(fy_start_year, basis)
    required = basis_tonnes * pct / 100
    cap = required + leftover_tonnes + required * c.PURCHASE_CAP_MARGIN_PCT / 100
    return {
        "target_pct": pct,
        "basis_fy": f"{basis_year(fy_start_year, basis)}-{str(basis_year(fy_start_year, basis) + 1)[2:]}",
        "required_tonnes": round(required, 2),
        "certificates_tonnes": round(certificates_tonnes, 2),
        "shortfall_tonnes": round(max(required - certificates_tonnes, 0.0), 2),
        "max_purchasable_tonnes": round(cap, 2),
        "over_purchased": certificates_tonnes > cap + 1e-9,
        "compliant": certificates_tonnes >= required,
    }


def certificate_tonnes(qp_tonnes: float, cf: float, route: str) -> float:
    """QEPR = Qp x CF x Wp."""
    return round(qp_tonnes * cf * c.WEIGHTAGE[route], 3)


def certificate_expiry(generated_fy_start: int) -> date:
    """Valid two years from the end of the FY in which generated (FY ends 31 Mar of start+1)."""
    return date(generated_fy_start + 1 + c.CERT_VALIDITY_YEARS_AFTER_FY_END, 3, 31)


def fy_start_year(d: date) -> int:
    return d.year if d.month >= 4 else d.year - 1


def price_band(ec_inr_per_tonne: float | None) -> tuple[float, float] | None:
    if ec_inr_per_tonne is None:
        return None
    lo, hi = c.PRICE_BAND_PCT_OF_EC
    return (ec_inr_per_tonne * lo / 100, ec_inr_per_tonne * hi / 100)
