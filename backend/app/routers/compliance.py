from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..calculations import constants as c
from ..calculations.epr import obligation
from ..calculations.ghg import ghg_savings
from ..calculations.integrity import run_checks
from ..db import get_db
from ..models import Collection, Dispatch, EPRProducer, EPRPurchase, Lot, ProcessingBatch

router = APIRouter(prefix="/api/compliance", tags=["compliance"])


@router.get("/integrity")
def integrity(severity: str | None = None, db: Session = Depends(get_db)):
    flags = run_checks(db.query(Collection).all(), db.query(Lot).all(),
                       db.query(ProcessingBatch).all(), db.query(Dispatch).all())
    return [f for f in flags if not severity or f["severity"] == severity]


@router.get("/epr")
def epr(db: Session = Depends(get_db)):
    out = []
    for p in db.query(EPRProducer).all():
        bought = db.query(func.coalesce(func.sum(EPRPurchase.tonnes), 0.0)).filter(EPRPurchase.producer_id == p.id).scalar()
        out.append({"producer": p.name, "fy": f"{p.fy_start_year}-{str(p.fy_start_year + 1)[2:]}",
                    "prior_year_sales_tonnes": p.prior_year_sales_tonnes,
                    **obligation(p.prior_year_sales_tonnes, p.fy_start_year, bought)})
    return out


@router.get("/epr/recycler-supply")
def recycler_supply(db: Session = Depends(get_db)):
    """ULO tonnes actually re-refined (base_oil batches) -- the supply side of EPR certificates."""
    rows = (db.query(ProcessingBatch).join(Lot).filter(Lot.material == "ULO", ProcessingBatch.product == "base_oil").all())
    by_recycler: dict[str, float] = {}
    for b in rows:
        by_recycler[b.processor.name] = by_recycler.get(b.processor.name, 0.0) + b.input_kg / 1000
    return [{"recycler": k, "recycled_tonnes": round(v, 2)} for k, v in by_recycler.items()]


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
