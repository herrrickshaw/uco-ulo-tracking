from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..calculations.integrity import run_checks
from ..calculations.quality import litres_to_kg
from ..db import get_db
from ..models import Collection, Dispatch, Lot, ProcessingBatch

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/summary")
def summary(db: Session = Depends(get_db)):
    cols = db.query(Collection).all()
    kg = {"UCO": 0.0, "ULO": 0.0}
    for col in cols:
        kg[col.material] += litres_to_kg(col.material, col.quantity_litres)
    out_by_product = dict(db.query(ProcessingBatch.product, func.sum(ProcessingBatch.output_kg)).group_by(ProcessingBatch.product).all())
    flags = run_checks(cols, db.query(Lot).all(), db.query(ProcessingBatch).all(), db.query(Dispatch).all())
    return {
        "uco_collected_tonnes": round(kg["UCO"] / 1000, 1),
        "ulo_collected_tonnes": round(kg["ULO"] / 1000, 1),
        "output_tonnes_by_product": {k: round(v / 1000, 1) for k, v in out_by_product.items()},
        "integrity_flags_high": sum(f["severity"] == "high" for f in flags),
        "integrity_flags_total": len(flags),
    }
