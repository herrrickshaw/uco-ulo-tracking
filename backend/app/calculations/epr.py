from . import constants as c


def target_pct(fy_start_year: int) -> float:
    if fy_start_year < min(c.EPR_TARGET_PCT):
        return 0.0
    return c.EPR_TARGET_PCT[min(fy_start_year, max(c.EPR_TARGET_PCT))]


def obligation(prior_year_sales_tonnes: float, fy_start_year: int, certificates_tonnes: float) -> dict:
    required = prior_year_sales_tonnes * target_pct(fy_start_year) / 100
    return {
        "target_pct": target_pct(fy_start_year),
        "required_tonnes": round(required, 2),
        "certificates_tonnes": round(certificates_tonnes, 2),
        "shortfall_tonnes": round(max(required - certificates_tonnes, 0.0), 2),
        "compliant": certificates_tonnes >= required,
    }
