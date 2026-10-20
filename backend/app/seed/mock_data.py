"""Mock data for every view, including deliberately planted anomalies so each integrity
check has something to show: a fresh-oil 'UCO' collection, a generator over its plausible
capacity, a duplicate manifest, an expired collector registration, an over-processed lot,
an over-yielding batch, and a non-compliant EPR producer."""

import random
from datetime import date, timedelta

from sqlalchemy.orm import Session

from ..calculations.quality import litres_to_kg
from ..models import (Collection, Collector, Dispatch, EPRProducer, EPRPurchase, Generator,
                      Lot, ProcessingBatch)

TODAY = date(2026, 10, 20)


def seed_if_empty(db: Session) -> None:
    if db.query(Generator).count():
        return
    rnd = random.Random(42)

    gens = [Generator(name=n, material="UCO", sector=s, state=st, monthly_purchase_litres=v, licence_ref=f"FSSAI-{i:05d}")
            for i, (n, s, st, v) in enumerate([
                ("Spice Route Restaurant", "restaurant", "Karnataka", 1500),
                ("Grand Plaza Hotel", "hotel", "Maharashtra", 4000),
                ("CrispBite Snacks Pvt Ltd", "food processor", "Gujarat", 20000),
                ("Campus Canteen Services", "institutional", "Tamil Nadu", 2500),
                ("Highway Dhaba Cluster", "restaurant", "Punjab", 1200),
            ], 1)]
    gens += [Generator(name=n, material="ULO", sector=s, state=st, monthly_purchase_litres=v, licence_ref=f"CPCB-HW-{i:04d}")
             for i, (n, s, st, v) in enumerate([
                 ("Metro Fleet Workshop", "garage", "Delhi", 3000),
                 ("Southern Steel Works", "industry", "Tamil Nadu", 8000),
                 ("Rapid Lube Service Chain", "garage", "Karnataka", 5000),
             ], 1)]
    ok = date(2027, 12, 31)
    cols = [
        Collector(name="GreenLoop UCO Collectors", role="collector", material="UCO", registration_ref="RUCO-C-101", registration_valid_until=ok),
        Collector(name="Bharat Oil Aggregators", role="aggregator", material="UCO", registration_ref="RUCO-A-201", registration_valid_until=ok),
        Collector(name="Lapsed Pickup Co", role="collector", material="UCO", registration_ref="RUCO-C-102", registration_valid_until=date(2026, 3, 31)),
        Collector(name="Deccan Biofuels", role="processor", material="UCO", registration_ref="RUCO-P-301", registration_valid_until=ok),
        Collector(name="EcoRecover Collection", role="collector", material="ULO", registration_ref="CPCB-EPR-C-11", registration_valid_until=ok),
        Collector(name="Enviro ULO Aggregation", role="aggregator", material="ULO", registration_ref="CPCB-EPR-A-12", registration_valid_until=ok),
        Collector(name="ReBase Re-refinery", role="recycler", material="ULO", registration_ref="CPCB-EPR-R-13", registration_valid_until=ok),
    ]
    db.add_all(gens + cols)
    db.flush()
    uco_gens = [g for g in gens if g.material == "UCO"]
    ulo_gens = [g for g in gens if g.material == "ULO"]
    c_uco, agg_uco, lapsed, proc_uco, c_ulo, agg_ulo, recycler = cols

    manifest = 0
    lots = []
    for m in range(6):  # six monthly lots per material
        start = date(2026, 4 + m, 1)
        for material, gl, col_, agg in (("UCO", uco_gens, c_uco, agg_uco), ("ULO", ulo_gens, c_ulo, agg_ulo)):
            lot = Lot(lot_code=f"{material}-{start:%Y%m}", material=material, aggregator_id=agg.id, formed_on=start + timedelta(days=27))
            db.add(lot)
            db.flush()
            lots.append(lot)
            for g in gl:
                manifest += 1
                litres = round(g.monthly_purchase_litres * rnd.uniform(0.25, 0.5))
                kw = ({"tpc_pct": round(rnd.uniform(18, 32), 1), "ffa_pct": round(rnd.uniform(2, 6), 1)} if material == "UCO"
                      else {"water_pct": round(rnd.uniform(0.5, 3.5), 1), "pcb_ppm": round(rnd.uniform(0, 8), 1),
                            "chlorine_ppm": round(rnd.uniform(100, 700))})
                db.add(Collection(manifest_no=f"M{manifest:05d}", generator_id=g.id, collector_id=col_.id, lot_id=lot.id,
                                  material=material, collected_on=start + timedelta(days=rnd.randint(2, 24)),
                                  quantity_litres=litres, **kw))
    db.flush()

    # ---- planted anomalies (latest month, so they are easy to spot) ----
    last = date(2026, 9, 10)
    lot_uco, lot_ulo = lots[-2], lots[-1]
    db.add(Collection(manifest_no="M90001", generator_id=uco_gens[0].id, collector_id=c_uco.id, lot_id=lot_uco.id,
                      material="UCO", collected_on=last, quantity_litres=1200, tpc_pct=3.1, ffa_pct=0.4))  # fresh oil
    db.add(Collection(manifest_no="M90002", generator_id=uco_gens[1].id, collector_id=c_uco.id, lot_id=lot_uco.id,
                      material="UCO", collected_on=last, quantity_litres=9000, tpc_pct=27.0, ffa_pct=4.0))  # over capacity
    db.add(Collection(manifest_no="M90003", generator_id=uco_gens[3].id, collector_id=lapsed.id, lot_id=lot_uco.id,
                      material="UCO", collected_on=last, quantity_litres=600, tpc_pct=24.0, ffa_pct=3.0))  # expired registration
    dup = db.query(Collection).first().manifest_no
    db.add(Collection(manifest_no=dup, generator_id=uco_gens[4].id, collector_id=c_uco.id, lot_id=lot_uco.id,
                      material="UCO", collected_on=last, quantity_litres=400, tpc_pct=22.0, ffa_pct=3.5))  # duplicate manifest
    db.add(Collection(manifest_no="M90004", generator_id=ulo_gens[0].id, collector_id=c_ulo.id, lot_id=lot_ulo.id,
                      material="ULO", collected_on=last, quantity_litres=300, water_pct=2.0, pcb_ppm=120.0, chlorine_ppm=400))  # PCB
    db.flush()

    # ---- processing + dispatch: honest batches for every lot except the planted ones ----
    n = 0
    for lot in lots:
        db.refresh(lot)
        received = sum(litres_to_kg(lot.material, c_.quantity_litres) for c_ in lot.collections)
        n += 1
        if lot.material == "UCO":
            product, proc, ratio, buyer = ("biodiesel", proc_uco, 0.88, "OMC blending terminal") if n % 2 else ("hefa_feedstock", proc_uco, 0.95, "SAF producer")
        else:
            product, proc, ratio, buyer = "base_oil", recycler, 0.68, "Lubricant blender"
        inp = received * 0.97  # ~3% water/sediment loss
        if lot is lot_ulo:
            inp = received * 1.15  # over-processed lot -> mass-balance flag
        out = inp * ratio
        if lot is lot_uco:
            product, ratio = "biodiesel", 0.88
            out = inp * 0.99  # impossible yield flag
        b = ProcessingBatch(batch_code=f"B-{lot.lot_code}", lot_id=lot.id, processor_id=proc.id, processed_on=lot.formed_on + timedelta(days=5),
                            product=product, input_kg=round(inp, 1), output_kg=round(out, 1))
        db.add(b)
        db.flush()
        send = out * 0.98 if lot is not lot_ulo else out * 1.1
        db.add(Dispatch(batch_id=b.id, buyer=buyer, dispatched_on=b.processed_on + timedelta(days=4), quantity_kg=round(send, 1)))

    # ---- EPR: FY2025-26, one compliant producer, one short ----
    recycled_t = sum(b.input_kg for b in db.query(ProcessingBatch).filter_by(product="base_oil")) / 1000
    p1 = EPRProducer(name="Meridian Lubricants", fy_start_year=2025, prior_year_sales_tonnes=max(recycled_t * 6, 100))
    p2 = EPRProducer(name="Coastal Base Oils", fy_start_year=2025, prior_year_sales_tonnes=max(recycled_t * 12, 200))
    db.add_all([p1, p2])
    db.flush()
    db.add(EPRPurchase(producer_id=p1.id, recycler_id=recycler.id, tonnes=round(p1.prior_year_sales_tonnes * 0.14, 2), purchased_on=date(2026, 6, 30)))
    db.add(EPRPurchase(producer_id=p2.id, recycler_id=recycler.id, tonnes=round(p2.prior_year_sales_tonnes * 0.05, 2), purchased_on=date(2026, 6, 30)))
    db.commit()
