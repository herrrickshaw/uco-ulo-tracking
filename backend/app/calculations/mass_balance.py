from __future__ import annotations

from . import constants as c
from .quality import litres_to_kg


def lot_totals(lot) -> tuple[float, float]:
    """(received_kg, processed_kg) for a Lot ORM row: collections converted litres->kg, batch inputs summed."""
    received = sum(litres_to_kg(lot.material, col.quantity_litres) for col in lot.collections)
    return received, sum(b.input_kg for b in lot.batches)


def lot_balance(received_kg: float, processed_kg: float) -> dict:
    """processed must not exceed received (within tolerance); remainder is stock/loss."""
    tol = received_kg * c.MASS_BALANCE_TOLERANCE_PCT / 100
    return {
        "received_kg": round(received_kg, 1),
        "processed_kg": round(processed_kg, 1),
        "unprocessed_kg": round(received_kg - processed_kg, 1),
        "balanced": processed_kg <= received_kg + tol,
    }


def yield_ok(product: str, input_kg: float, output_kg: float) -> bool:
    """True if output/input is inside the configured yield range for ``product`` (kg in, kg out)."""
    if input_kg <= 0:
        return False
    lo, hi = c.YIELD_RANGE[product]
    return lo <= output_kg / input_kg <= hi
