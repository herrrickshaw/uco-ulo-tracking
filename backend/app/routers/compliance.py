from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..calculations import constants as c
from ..calculations import ledger
from ..calculations.epr import certificate_expiry, obligation, price_band
from ..calculations.ghg import ghg_savings
from ..calculations.integrity import run_checks
from ..calculations.returns import status as return_status
from ..db import get_db
from ..models import (Collection, Collector, Dispatch, EPRCertificate, EPRProducer, EPRPurchase, Lot,
                      ProcessingBatch, ReturnFiling, Shipment)

router = APIRouter(prefix="/api/compliance", tags=["compliance"])


@router.get("/integrity")
def integrity(severity: str | None = None, db: Session = Depends(get_db)):
    flags = run_checks(db.query(Collection).all(), db.query(Lot).all(), db.query(ProcessingBatch).all(),
                       db.query(Dispatch).all(), db.query(Shipment).all())
    chain = ledger.verify(db)
    for p in chain["problems"]:
        flags.append({"check": "ledger_" + ("chain_broken" if p["problem"] == "chain_broken" else "record_changed"),
                      "ref": f"ledger entry {p['entry']}", "detail": p["problem"], "severity": "high"})
    return [f for f in flags if not severity or f["severity"] == severity]


def _epr_bought(db, producer_id):
    return db.query(func.coalesce(func.sum(EPRPurchase.tonnes), 0.0)).filter(EPRPurchase.producer_id == producer_id).scalar()


@router.get("/epr")
def epr(db: Session = Depends(get_db)):
    out = []
    for p in db.query(EPRProducer).all():
        out.append({"producer": p.name, "producer_type": p.producer_type, "basis": p.obligation_basis,
                    "fy": f"{p.fy_start_year}-{str(p.fy_start_year + 1)[2:]}", "basis_tonnes": p.basis_tonnes,
                    **obligation(p.basis_tonnes, p.fy_start_year, _epr_bought(db, p.id), p.obligation_basis)})
    return out


@router.get("/epr/certificates")
def certificate_ledger(db: Session = Depends(get_db)):
    """Per-recycler Generated / Transferred / Available (MT), mirroring the CPCB portal dashboard."""
    out = []
    for r in db.query(Collector).filter(Collector.role == "recycler").all():
        gen = db.query(func.coalesce(func.sum(EPRCertificate.tonnes), 0.0)).filter(EPRCertificate.recycler_id == r.id).scalar()
        xfer = db.query(func.coalesce(func.sum(EPRPurchase.tonnes), 0.0)).filter(EPRPurchase.recycler_id == r.id).scalar()
        out.append({"recycler": r.name, "state": r.state, "generated_mt": round(gen, 3), "transferred_mt": round(xfer, 3),
                    "available_mt": round(gen - xfer, 3)})
    return out


class PurchaseIn(BaseModel):
    producer_id: int
    recycler_id: int
    certificate_fy: int
    tonnes: float
    price_inr_per_tonne: float | None = None
    purchased_on: date


@router.post("/epr/purchases")
def transfer_certificates(payload: PurchaseIn, db: Session = Depends(get_db)):
    """Recycler -> producer transfer with the portal's rules enforced."""
    prod, rec = db.get(EPRProducer, payload.producer_id), db.get(Collector, payload.recycler_id)
    if not prod or not rec:
        raise HTTPException(404, "Producer or recycler not found")
    if rec.role != "recycler":
        raise HTTPException(400, "Certificates can only be bought from a registered recycler (not tradable between producers)")
    if certificate_expiry(payload.certificate_fy) < payload.purchased_on:
        raise HTTPException(400, f"Certificates generated in FY{payload.certificate_fy} expired on {certificate_expiry(payload.certificate_fy)}")
    gen = db.query(func.coalesce(func.sum(EPRCertificate.tonnes), 0.0)).filter(
        EPRCertificate.recycler_id == rec.id, EPRCertificate.fy_start_year == payload.certificate_fy).scalar()
    sold = db.query(func.coalesce(func.sum(EPRPurchase.tonnes), 0.0)).filter(
        EPRPurchase.recycler_id == rec.id, EPRPurchase.certificate_fy == payload.certificate_fy).scalar()
    if payload.tonnes > gen - sold + 1e-9:
        raise HTTPException(400, f"Recycler has only {gen - sold:.3f} t of FY{payload.certificate_fy} certificates available")
    ob = obligation(prod.basis_tonnes, prod.fy_start_year, _epr_bought(db, prod.id) + payload.tonnes, prod.obligation_basis)
    if ob["over_purchased"]:
        raise HTTPException(400, f"Exceeds purchase cap of {ob['max_purchasable_tonnes']} t (liability + 10%)")
    band = price_band(c.EC_INR_PER_TONNE)
    if band and payload.price_inr_per_tonne is not None and not band[0] <= payload.price_inr_per_tonne <= band[1]:
        raise HTTPException(400, f"Price outside CPCB band {band[0]:.0f}-{band[1]:.0f} INR/t")
    row = EPRPurchase(**payload.model_dump())
    db.add(row)
    db.commit()
    return {"id": row.id, **ob}


@router.get("/epr/recycler-supply")
def recycler_supply(db: Session = Depends(get_db)):
    """ULO tonnes actually processed per recycler and route (the supply side of EPR certificates)."""
    out: dict[tuple, float] = {}
    for cert in db.query(EPRCertificate).all():
        key = (cert.recycler.name, cert.route)
        out[key] = out.get(key, 0.0) + cert.qp_tonnes
    return [{"recycler": k[0], "route": k[1], "end_product_tonnes": round(v, 2)} for k, v in out.items()]


@router.get("/returns")
def returns(as_of: date | None = None, db: Session = Depends(get_db)):
    as_of = as_of or date.today()
    return [{"entity": r.entity_name, "role": r.entity_role, "period": r.period, "due_on": r.due_on,
             "filed_on": r.filed_on, "status": return_status(r.due_on, r.filed_on, as_of)}
            for r in db.query(ReturnFiling).order_by(ReturnFiling.due_on).all()]


@router.get("/ledger")
def ledger_status(db: Session = Depends(get_db)):
    return ledger.verify(db)


@router.get("/ghg")
def ghg(db: Session = Depends(get_db)):
    out = []
    for b in db.query(ProcessingBatch).join(Lot).filter(Lot.material == "UCO").all():
        g = ghg_savings(b.product, b.output_kg)
        if g:
            out.append({"batch": b.batch_code, "product": b.product, "output_kg": b.output_kg, **g})
    return out


@router.get("/parameters")
def parameters():
    """The editable defaults in use, so reviewers can see what to verify."""
    return {k: getattr(c, k) for k in dir(c) if k.isupper()}
