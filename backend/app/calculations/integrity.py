"""Fraud / data-integrity checks.  Pure functions over ORM rows so they are unit-testable."""
from collections import Counter, defaultdict

from . import constants as c
from .mass_balance import lot_balance, yield_ok
from .quality import litres_to_kg, registration_valid, uco_quality_flags, ulo_quality_flags


def run_checks(collections, lots, batches, dispatches) -> list[dict]:
    flags: list[dict] = []

    def add(kind, ref, detail, severity="high"):
        flags.append({"check": kind, "ref": ref, "detail": detail, "severity": severity})

    manifest_counts = Counter(col.manifest_no for col in collections)
    monthly: dict[tuple, float] = defaultdict(float)

    for col in collections:
        ref = f"collection {col.manifest_no}"
        if manifest_counts[col.manifest_no] > 1:
            add("duplicate_manifest", ref, "manifest number used on more than one collection")
        if not registration_valid(col.collector.registration_valid_until, col.collected_on):
            add("collector_registration", ref, f"{col.collector.name} registration missing/expired on {col.collected_on}")
        if col.material == "UCO":
            q = uco_quality_flags(col.tpc_pct, col.ffa_pct)
            if "suspiciously_fresh" in q:
                add("suspiciously_fresh_uco", ref, f"TPC {col.tpc_pct}% < {c.UCO_SUSPICIOUSLY_FRESH_TPC_PCT}% -- possible fresh/blended oil")
            if "tpc_missing" in q:
                add("tpc_missing", ref, "no TPC test recorded", "medium")
        else:
            for q in ulo_quality_flags(col.water_pct, col.pcb_ppm, col.chlorine_ppm):
                add(q, ref, "ULO acceptance threshold exceeded", "medium" if q != "pcb_hazard_segregate" else "high")
        monthly[(col.generator_id, col.collected_on.year, col.collected_on.month)] += col.quantity_litres

    gens = {col.generator_id: col.generator for col in collections}
    for (gid, y, m), litres in monthly.items():
        g = gens[gid]
        cap = g.monthly_purchase_litres * c.MAX_RECOVERABLE_FRACTION[g.material]
        if litres > cap:
            add("generator_over_capacity", f"{g.name} {y}-{m:02d}",
                f"{litres:.0f} L collected vs plausible max {cap:.0f} L from declared purchases")

    for lot in lots:
        received = sum(litres_to_kg(lot.material, col.quantity_litres) for col in lot.collections)
        processed = sum(b.input_kg for b in lot.batches)
        if not lot_balance(received, processed)["balanced"]:
            add("mass_balance", f"lot {lot.lot_code}", f"processed {processed:.0f} kg > received {received:.0f} kg")

    for b in batches:
        ref = f"batch {b.batch_code}"
        if b.product not in c.PRODUCTS_BY_MATERIAL[b.lot.material]:
            add("product_mismatch", ref, f"{b.product} is not a valid product of {b.lot.material}")
        elif not yield_ok(b.product, b.input_kg, b.output_kg):
            add("implausible_yield", ref, f"{b.output_kg / b.input_kg:.0%} yield outside {c.YIELD_RANGE[b.product]}")
        out = sum(d.quantity_kg for d in b.dispatches)
        if out > b.output_kg * (1 + c.MASS_BALANCE_TOLERANCE_PCT / 100):
            add("dispatch_exceeds_output", ref, f"dispatched {out:.0f} kg > produced {b.output_kg:.0f} kg")
    return flags
