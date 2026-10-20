from . import constants as c


def ghg_savings(product: str, output_kg: float) -> dict | None:
    """Indicative GHG saving vs fossil diesel for UCO-derived fuel output."""
    if product not in c.GHG_DEFAULT_G_PER_MJ:
        return None
    mj = output_kg * c.LHV_MJ_PER_KG[product]
    intensity = c.GHG_DEFAULT_G_PER_MJ[product]
    saved_t = (c.FOSSIL_DIESEL_COMPARATOR_G_PER_MJ - intensity) * mj / 1e6
    return {
        "intensity_g_per_mj": intensity,
        "savings_pct": round((1 - intensity / c.FOSSIL_DIESEL_COMPARATOR_G_PER_MJ) * 100, 1),
        "tco2e_saved": round(saved_t, 2),
    }
