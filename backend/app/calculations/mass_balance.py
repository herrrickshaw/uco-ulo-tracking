from . import constants as c


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
    if input_kg <= 0:
        return False
    lo, hi = c.YIELD_RANGE[product]
    return lo <= output_kg / input_kg <= hi
