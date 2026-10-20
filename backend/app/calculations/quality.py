from datetime import date

from . import constants as c


def uco_quality_flags(tpc_pct: float | None, ffa_pct: float | None = None) -> list[str]:
    flags = []
    if tpc_pct is None:
        flags.append("tpc_missing")
    elif tpc_pct < c.UCO_SUSPICIOUSLY_FRESH_TPC_PCT:
        flags.append("suspiciously_fresh")
    return flags


def ulo_quality_flags(water_pct, pcb_ppm, chlorine_ppm) -> list[str]:
    flags = []
    if water_pct is not None and water_pct > c.ULO_MAX_WATER_PCT:
        flags.append("high_water")
    if pcb_ppm is not None and pcb_ppm >= c.ULO_PCB_HAZARD_PPM:
        flags.append("pcb_hazard_segregate")
    if chlorine_ppm is not None and chlorine_ppm > c.ULO_MAX_CHLORINE_PPM:
        flags.append("high_chlorine")
    return flags


def registration_valid(valid_until: date | None, on: date) -> bool:
    return valid_until is not None and valid_until >= on


def litres_to_kg(material: str, litres: float) -> float:
    return litres * c.DENSITY_KG_PER_L[material]
