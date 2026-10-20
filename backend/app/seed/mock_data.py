"""Mock data for every view, including deliberately planted anomalies so each integrity
check has something to show: a fresh-oil 'UCO' collection, a generator over its plausible
capacity, a duplicate manifest, an expired collector registration, an over-processed lot,
an over-yielding batch, and a non-compliant EPR producer."""

import random
from datetime import date, timedelta

from sqlalchemy.orm import Session

from ..calculations import ledger
from ..calculations.epr import certificate_tonnes, fy_start_year
from ..calculations.quality import litres_to_kg
from ..calculations.returns import annual_due, quarter_due
from ..models import (Collection, Collector, Dispatch, EPRCertificate, EPRProducer, EPRPurchase, Generator,
                      Lot, ProcessingBatch, ReturnFiling, Shipment)

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
        Collector(name="EcoRecover Collection", role="collector", material="ULO", registration_ref="CPCB-EPR-C-11", registration_valid_until=ok,
                  state="Delhi", ca_level=1, has_storage=False),
        Collector(name="Enviro ULO Aggregation", role="aggregator", material="ULO", registration_ref="CPCB-EPR-A-12", registration_valid_until=ok,
                  state="Delhi", ca_level=2, has_storage=True),
        Collector(name="ReBase Re-refinery", role="recycler", material="ULO", registration_ref="CPCB-EPR-R-13", registration_valid_until=ok,
                  state="Gujarat", conversion_factor=1.5),
        Collector(name="RoadRunner Used Oil", role="collector", material="ULO", registration_ref="CPCB-EPR-C-14", registration_valid_until=ok,
                  state="Haryana", ca_level=1, has_storage=True),  # CA-1 holding storage -> flag
    ]
    db.add_all(gens + cols)
    db.flush()
    uco_gens = [g for g in gens if g.material == "UCO"]
    ulo_gens = [g for g in gens if g.material == "ULO"]
    c_uco, agg_uco, lapsed, proc_uco, c_ulo, agg_ulo, recycler, roadrunner = cols

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

    # ---- shipments: aggregator -> processor/recycler per lot, with planted transport anomalies ----
    for k, lot in enumerate(lots):
        b = db.query(ProcessingBatch).filter_by(lot_id=lot.id).one()
        sender, receiver = (agg_uco, proc_uco) if lot.material == "UCO" else (agg_ulo, recycler)
        kg = round(b.input_kg, 1)
        db.add(Shipment(manifest_no=f"F10-{lot.lot_code}", material=lot.material, sender_id=sender.id, receiver_id=receiver.id,
                        lot_id=lot.id, vehicle_no=f"MH12-AB-{1000 + k}", dispatched_on=lot.formed_on + timedelta(days=1),
                        received_on=lot.formed_on + timedelta(days=2), dispatched_kg=kg, received_kg=round(kg * 0.995, 1),
                        distance_km=60.0 if lot.material == "ULO" else 40.0))
    db.add(Shipment(manifest_no="F10-BAD1", material="ULO", sender_id=c_ulo.id, receiver_id=agg_ulo.id, vehicle_no="DL01-ZZ-9999",
                    gps_tracked=False, nhwts_registered=False, dispatched_on=date(2026, 9, 12), received_on=date(2026, 9, 12),
                    dispatched_kg=2000.0, received_kg=1700.0, distance_km=40.0))           # no GPS/NHWTS + 15% shortfall
    db.add(Shipment(manifest_no="F10-BAD2", material="ULO", sender_id=roadrunner.id, receiver_id=agg_ulo.id, vehicle_no="HR26-CA-0001",
                    max_container_l=1000.0, dispatched_on=date(2026, 9, 14), received_on=date(2026, 9, 14),
                    dispatched_kg=900.0, received_kg=900.0, distance_km=210.0))           # CA-1: big tank, 210 km
    db.flush()

    # ---- EPR certificates: QEPR = Qp x CF x Wp per ULO batch, recycler = ReBase ----
    for b in db.query(ProcessingBatch).join(Lot).filter(Lot.material == "ULO").all():
        route = "re_refining"
        wp = 1.0
        qp = b.output_kg / 1000
        db.add(EPRCertificate(batch_id=b.id, recycler_id=recycler.id, fy_start_year=fy_start_year(b.processed_on), route=route,
                              qp_tonnes=round(qp, 3), cf=recycler.conversion_factor, wp=wp,
                              tonnes=certificate_tonnes(qp, recycler.conversion_factor, route)))
    db.flush()
    total_cert = sum(c_.tonnes for c_ in db.query(EPRCertificate).all())

    # ---- EPR producers, obligation year FY2026-27 (20% of Y-2 = FY2024-25 sales) ----
    p1 = EPRProducer(name="Meridian Lubricants", fy_start_year=2026, producer_type="P3", basis_tonnes=round(total_cert * 0.5 / 0.20, 1))
    p2 = EPRProducer(name="Coastal Base Oils", fy_start_year=2026, producer_type="P1", basis_tonnes=round(total_cert * 0.8 / 0.20, 1))
    db.add_all([p1, p2])
    db.flush()
    db.add(EPRPurchase(producer_id=p1.id, recycler_id=recycler.id, certificate_fy=2026, tonnes=round(total_cert * 0.52, 3), purchased_on=date(2026, 9, 30)))
    db.add(EPRPurchase(producer_id=p2.id, recycler_id=recycler.id, certificate_fy=2026, tonnes=round(total_cert * 0.30, 3), purchased_on=date(2026, 9, 30)))

    # ---- return filings (one overdue, one late) ----
    for ent, role in ((c_ulo.name, "collector"), (agg_ulo.name, "collector"), (recycler.name, "recycler")):
        db.add(ReturnFiling(entity_name=ent, entity_role=role, period="Q1 FY2026-27", due_on=quarter_due(2026, 1), filed_on=date(2026, 7, 20)))
    db.add(ReturnFiling(entity_name=roadrunner.name, entity_role="collector", period="Q1 FY2026-27", due_on=quarter_due(2026, 1), filed_on=date(2026, 8, 12)))  # late
    db.add(ReturnFiling(entity_name=recycler.name, entity_role="recycler", period="Q2 FY2026-27", due_on=quarter_due(2026, 2), filed_on=None))  # overdue on 2026-10-20? due 31 Oct -> still due
    db.add(ReturnFiling(entity_name=agg_ulo.name, entity_role="collector", period="Annual FY2025-26", due_on=annual_due(2025, "Annual FY2025-26"), filed_on=None))
    db.add(ReturnFiling(entity_name=roadrunner.name, entity_role="collector", period="Annual FY2024-25", due_on=annual_due(2024), filed_on=None))  # overdue
    db.commit()

    # ---- hash-chained custody ledger over every logged event (tamper-evidence) ----
    for kind, model in ledger.KINDS.items():
        for row in db.query(model).order_by(model.id).all():
            ledger.append(db, kind, row)
