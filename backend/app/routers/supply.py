from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from ..calculations import constants as c
from ..calculations import ledger
from ..calculations.mass_balance import lot_balance
from ..calculations.quality import litres_to_kg
from ..db import get_db
from ..models import Collection, Collector, Dispatch, Generator, Lot, ProcessingBatch, Shipment

router = APIRouter(prefix="/api", tags=["supply-chain"])


class GeneratorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    material: str
    sector: str
    state: str
    monthly_purchase_litres: float
    licence_ref: str


class CollectorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    role: str
    material: str
    registration_ref: str
    registration_valid_until: date | None
    state: str
    ca_level: int | None
    has_storage: bool


class CollectionIn(BaseModel):
    manifest_no: str
    generator_id: int
    collector_id: int
    lot_id: int | None = None
    material: str
    collected_on: date
    quantity_litres: float
    tpc_pct: float | None = None
    ffa_pct: float | None = None
    water_pct: float | None = None
    pcb_ppm: float | None = None
    chlorine_ppm: float | None = None
    ruco_request_id: str = ""
    evidence_ref: str = ""


class CollectionOut(CollectionIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class BatchIn(BaseModel):
    batch_code: str
    lot_id: int
    processor_id: int
    processed_on: date
    product: str
    input_kg: float
    output_kg: float
    unfit_declaration_ref: str = ""


class BatchOut(BatchIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class DispatchIn(BaseModel):
    batch_id: int
    buyer: str
    dispatched_on: date
    quantity_kg: float


class DispatchOut(DispatchIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class ShipmentIn(BaseModel):
    manifest_no: str
    material: str
    sender_id: int
    receiver_id: int
    lot_id: int | None = None
    vehicle_no: str
    gps_tracked: bool = True
    nhwts_registered: bool = True
    spcb_intimated: bool = True
    max_container_l: float = 200.0
    distance_km: float = 0.0
    dispatched_on: date
    received_on: date | None = None
    dispatched_kg: float
    received_kg: float | None = None


class ShipmentOut(ShipmentIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


@router.get("/generators", response_model=list[GeneratorOut])
def list_generators(material: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Generator)
    return q.filter(Generator.material == material).all() if material else q.all()


@router.get("/collectors", response_model=list[CollectorOut])
def list_collectors(db: Session = Depends(get_db)):
    return db.query(Collector).all()


@router.get("/collections", response_model=list[CollectionOut])
def list_collections(material: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Collection).order_by(Collection.collected_on.desc())
    return q.filter(Collection.material == material).all() if material else q.all()


@router.post("/collections", response_model=CollectionOut)
def create_collection(payload: CollectionIn, db: Session = Depends(get_db)):
    gen = db.get(Generator, payload.generator_id)
    if not gen or not db.get(Collector, payload.collector_id):
        raise HTTPException(404, "Generator or collector not found")
    if gen.material != payload.material:
        raise HTTPException(400, f"Generator handles {gen.material}, not {payload.material}")
    row = Collection(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    ledger.append(db, "collection", row)
    return row


@router.get("/lots")
def list_lots(db: Session = Depends(get_db)):
    out = []
    for lot in db.query(Lot).order_by(Lot.formed_on.desc()).all():
        received = sum(litres_to_kg(lot.material, col.quantity_litres) for col in lot.collections)
        processed = sum(b.input_kg for b in lot.batches)
        out.append({"id": lot.id, "lot_code": lot.lot_code, "material": lot.material,
                    "aggregator": lot.aggregator.name, "formed_on": lot.formed_on,
                    "n_collections": len(lot.collections), **lot_balance(received, processed)})
    return out


@router.get("/batches", response_model=list[BatchOut])
def list_batches(db: Session = Depends(get_db)):
    return db.query(ProcessingBatch).order_by(ProcessingBatch.processed_on.desc()).all()


@router.post("/batches", response_model=BatchOut)
def create_batch(payload: BatchIn, db: Session = Depends(get_db)):
    lot = db.get(Lot, payload.lot_id)
    if not lot:
        raise HTTPException(404, "Lot not found")
    if payload.product not in c.PRODUCTS_BY_MATERIAL[lot.material]:
        raise HTTPException(400, f"{payload.product} is not a product of {lot.material}")
    row = ProcessingBatch(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    ledger.append(db, "batch", row)
    return row


@router.get("/dispatches", response_model=list[DispatchOut])
def list_dispatches(db: Session = Depends(get_db)):
    return db.query(Dispatch).all()


@router.post("/dispatches", response_model=DispatchOut)
def create_dispatch(payload: DispatchIn, db: Session = Depends(get_db)):
    if not db.get(ProcessingBatch, payload.batch_id):
        raise HTTPException(404, "Batch not found")
    row = Dispatch(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    ledger.append(db, "dispatch", row)
    return row


@router.get("/shipments", response_model=list[ShipmentOut])
def list_shipments(db: Session = Depends(get_db)):
    return db.query(Shipment).order_by(Shipment.dispatched_on.desc()).all()


@router.post("/shipments", response_model=ShipmentOut)
def create_shipment(payload: ShipmentIn, db: Session = Depends(get_db)):
    if not db.get(Collector, payload.sender_id) or not db.get(Collector, payload.receiver_id):
        raise HTTPException(404, "Sender or receiver not found")
    row = Shipment(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    ledger.append(db, "shipment", row)
    return row
