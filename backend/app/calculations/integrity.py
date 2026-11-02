"""Fraud / data-integrity checks.  Pure functions over ORM rows so they are unit-testable."""
from __future__ import annotations

from collections import Counter, defaultdict
from functools import partial

from . import constants as c
from .mass_balance import lot_balance, lot_totals, yield_ok
from .quality import registration_valid, uco_quality_flags, ulo_quality_flags

Flags = list[dict]


def _flag(flags: Flags, kind: str, ref: str, detail: str, severity: str = "high") -> None:
    flags.append({"check": kind, "ref": ref, "detail": detail, "severity": severity})


def _check_collections(flags: Flags, collections) -> dict:
    """Per-collection checks (manifest, registration, quality). Returns litres collected per (generator, year, month)."""
    add = partial(_flag, flags)
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
    return monthly


def _check_generator_capacity(flags: Flags, collections, monthly: dict) -> None:
    """Flag generators whose monthly collections exceed what their declared purchases could yield."""
    gens = {col.generator_id: col.generator for col in collections}
    for (gid, y, m), litres in monthly.items():
        g = gens[gid]
        cap = g.monthly_purchase_litres * c.MAX_RECOVERABLE_FRACTION[g.material]
        if litres > cap:
            _flag(flags, "generator_over_capacity", f"{g.name} {y}-{m:02d}",
                  f"{litres:.0f} L collected vs plausible max {cap:.0f} L from declared purchases")


def _check_lots(flags: Flags, lots) -> None:
    """Flag lots where more was processed than received."""
    for lot in lots:
        received, processed = lot_totals(lot)
        if not lot_balance(received, processed)["balanced"]:
            _flag(flags, "mass_balance", f"lot {lot.lot_code}", f"processed {processed:.0f} kg > received {received:.0f} kg")


def _check_batches(flags: Flags, batches) -> None:
    """Product validity, yield range, co-processing declaration and dispatch-vs-output checks."""
    add = partial(_flag, flags)
    for b in batches:
        ref = f"batch {b.batch_code}"
        if b.product not in c.PRODUCTS_BY_MATERIAL[b.lot.material]:
            add("product_mismatch", ref, f"{b.product} is not a valid product of {b.lot.material}")
        elif not yield_ok(b.product, b.input_kg, b.output_kg):
            add("implausible_yield", ref, f"{b.output_kg / b.input_kg:.0%} yield outside {c.YIELD_RANGE[b.product]}")
        if b.product == "fuel_oil" and not b.unfit_declaration_ref:
            add("coprocessing_without_declaration", ref, "co-processing needs a declaration that the oil is unfit for re-refining")
        out = sum(d.quantity_kg for d in b.dispatches)
        if out > b.output_kg * (1 + c.MASS_BALANCE_TOLERANCE_PCT / 100):
            add("dispatch_exceeds_output", ref, f"dispatched {out:.0f} kg > produced {b.output_kg:.0f} kg")


def _check_shipments(flags: Flags, shipments) -> None:
    """Transport, registration, transit-loss and CA-1 collection-agent rules."""
    add = partial(_flag, flags)
    for sh in shipments:
        ref = f"shipment {sh.manifest_no}"
        if sh.material == "ULO":
            if not sh.nhwts_registered:
                add("vehicle_not_in_nhwts", ref, f"vehicle {sh.vehicle_no} not registered in the hazardous-waste tracking system")
            if not sh.gps_tracked:
                add("vehicle_no_gps", ref, f"vehicle {sh.vehicle_no} not GPS-tracked (required for used-oil transport)")
            if not sh.spcb_intimated:
                add("spcb_not_intimated", ref, "sender did not intimate the State Pollution Control Board", "medium")
        if not registration_valid(sh.receiver.registration_valid_until, sh.dispatched_on):
            add("receiver_registration", ref, f"{sh.receiver.name} registration missing/expired on {sh.dispatched_on}")
        if sh.received_kg is not None and sh.dispatched_kg > 0:
            var = abs(sh.received_kg - sh.dispatched_kg) / sh.dispatched_kg * 100
            if var > c.TRANSIT_LOSS_TOLERANCE_PCT:
                add("transit_variance", ref, f"received {sh.received_kg:.0f} kg vs dispatched {sh.dispatched_kg:.0f} kg ({var:.1f}% off)")
        s = sh.sender
        if sh.material == "ULO" and s.ca_level == 1:
            if s.has_storage:
                add("ca1_has_storage", ref, f"{s.name} is registered CA-1 (no storage) but holds storage")
            if sh.max_container_l > c.CA1_MAX_CONTAINER_L:
                add("ca1_container_too_large", ref, f"CA-1 container {sh.max_container_l:.0f} L > {c.CA1_MAX_CONTAINER_L:.0f} L")
            if sh.distance_km > c.CA1_RADIUS_NO_RECYCLER_KM:
                add("ca1_out_of_radius", ref, f"CA-1 haul {sh.distance_km:.0f} km exceeds even the {c.CA1_RADIUS_NO_RECYCLER_KM:.0f} km no-recycler limit")
            elif sh.distance_km > c.CA1_RADIUS_KM:
                add("ca1_out_of_radius", ref, f"CA-1 haul {sh.distance_km:.0f} km > {c.CA1_RADIUS_KM:.0f} km (allowed only if no recycler/CA-2 nearby)", "medium")


def run_checks(collections, lots, batches, dispatches, shipments=()) -> list[dict]:
    """Run every integrity check over ORM rows; returns flag dicts {check, ref, detail, severity}.

    ``dispatches`` is accepted for API compatibility; dispatch totals are read via ``batch.dispatches``.
    """
    flags: Flags = []
    monthly = _check_collections(flags, collections)
    _check_generator_capacity(flags, collections, monthly)
    _check_lots(flags, lots)
    _check_batches(flags, batches)
    _check_shipments(flags, shipments)
    return flags
