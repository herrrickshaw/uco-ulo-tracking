from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base

# material: "UCO" (used cooking oil) | "ULO" (used lubricating oil)


class Generator(Base):
    """A point source: restaurant/hotel/food processor (UCO) or garage/workshop/industry (ULO)."""

    __tablename__ = "generators"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    material: Mapped[str] = mapped_column(String)
    sector: Mapped[str] = mapped_column(String)  # e.g. restaurant, hotel, garage
    state: Mapped[str] = mapped_column(String)
    # Declared virgin oil / lubricant purchased per month; caps plausible recovery
    monthly_purchase_litres: Mapped[float] = mapped_column(Float)
    licence_ref: Mapped[str] = mapped_column(String, default="")  # FSSAI licence / CPCB authorisation
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)

    collections: Mapped[list["Collection"]] = relationship(back_populates="generator")


class Collector(Base):
    """Aggregator / authorised collector / recycler. registration_valid_until drives the registration check."""

    __tablename__ = "collectors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)  # collector | aggregator | processor | recycler
    material: Mapped[str] = mapped_column(String)
    registration_ref: Mapped[str] = mapped_column(String, default="")  # RUCO portal ID / CPCB EPR registration
    registration_valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    state: Mapped[str] = mapped_column(String, default="")
    # CPCB used-oil collection-agent level: 1 (no storage) | 2 (storage) | None for non-agents
    ca_level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    has_storage: Mapped[bool] = mapped_column(Boolean, default=False)
    # Recycler only: CPCB-determined conversion factor (input per unit output) for QEPR = Qp x CF x Wp
    conversion_factor: Mapped[float] = mapped_column(Float, default=1.5)


class Collection(Base):
    __tablename__ = "collections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    manifest_no: Mapped[str] = mapped_column(String)  # RUCO disposal request / HW manifest number
    generator_id: Mapped[int] = mapped_column(ForeignKey("generators.id"))
    collector_id: Mapped[int] = mapped_column(ForeignKey("collectors.id"))
    lot_id: Mapped[int | None] = mapped_column(ForeignKey("lots.id"), nullable=True)
    material: Mapped[str] = mapped_column(String)
    collected_on: Mapped[date] = mapped_column(Date)
    quantity_litres: Mapped[float] = mapped_column(Float)
    # UCO quality
    tpc_pct: Mapped[float | None] = mapped_column(Float, nullable=True)  # total polar compounds
    ffa_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    # ULO quality
    water_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    pcb_ppm: Mapped[float | None] = mapped_column(Float, nullable=True)
    chlorine_ppm: Mapped[float | None] = mapped_column(Float, nullable=True)
    ruco_request_id: Mapped[str] = mapped_column(String, default="")  # FSSAI RUCO disposal request (UCO)
    evidence_ref: Mapped[str] = mapped_column(String, default="")  # weighing ticket / scale ID / photo

    generator: Mapped["Generator"] = relationship(back_populates="collections")
    collector: Mapped["Collector"] = relationship()
    lot: Mapped["Lot | None"] = relationship(back_populates="collections")


class Lot(Base):
    """Aggregated consolidation lot -- the unit mass balance is checked on."""

    __tablename__ = "lots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lot_code: Mapped[str] = mapped_column(String, unique=True)
    material: Mapped[str] = mapped_column(String)
    aggregator_id: Mapped[int] = mapped_column(ForeignKey("collectors.id"))
    formed_on: Mapped[date] = mapped_column(Date)

    aggregator: Mapped["Collector"] = relationship()
    collections: Mapped[list["Collection"]] = relationship(back_populates="lot")
    batches: Mapped[list["ProcessingBatch"]] = relationship(back_populates="lot")


class ProcessingBatch(Base):
    __tablename__ = "processing_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_code: Mapped[str] = mapped_column(String, unique=True)
    lot_id: Mapped[int] = mapped_column(ForeignKey("lots.id"))
    processor_id: Mapped[int] = mapped_column(ForeignKey("collectors.id"))
    processed_on: Mapped[date] = mapped_column(Date)
    # biodiesel | hefa_feedstock (pretreated UCO) | base_oil (re-refined ULO) | fuel_oil
    product: Mapped[str] = mapped_column(String)
    input_kg: Mapped[float] = mapped_column(Float)
    output_kg: Mapped[float] = mapped_column(Float)
    # Co-processing (fuel_oil) is only for used oil declared unfit for re-refining
    unfit_declaration_ref: Mapped[str] = mapped_column(String, default="")

    lot: Mapped["Lot"] = relationship(back_populates="batches")
    processor: Mapped["Collector"] = relationship()
    dispatches: Mapped[list["Dispatch"]] = relationship(back_populates="batch")


class Dispatch(Base):
    __tablename__ = "dispatches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("processing_batches.id"))
    buyer: Mapped[str] = mapped_column(String)  # OMC blender, SAF producer, lube blender ...
    dispatched_on: Mapped[date] = mapped_column(Date)
    quantity_kg: Mapped[float] = mapped_column(Float)

    batch: Mapped["ProcessingBatch"] = relationship(back_populates="dispatches")


class EPRProducer(Base):
    """Obligated entity under the used-oil EPR chapter (producer P1-P9, or used-oil importer)."""

    __tablename__ = "epr_producers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    fy_start_year: Mapped[int] = mapped_column(Integer)  # obligation year: FY2026-27 -> 2026
    obligation_basis: Mapped[str] = mapped_column(String, default="producer")  # producer | used_oil_importer
    producer_type: Mapped[str] = mapped_column(String, default="P3")  # CPCB portal code P1..P9
    # producer: base/lube oil sold or imported in year Y-2; importer: used oil imported in Y-1
    basis_tonnes: Mapped[float] = mapped_column(Float)


class EPRCertificate(Base):
    """Certificate quantity generated for a recycler from one processing batch: QEPR = Qp x CF x Wp."""

    __tablename__ = "epr_certificates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("processing_batches.id"), unique=True)
    recycler_id: Mapped[int] = mapped_column(ForeignKey("collectors.id"))
    fy_start_year: Mapped[int] = mapped_column(Integer)  # FY of generation
    route: Mapped[str] = mapped_column(String)  # re_refining | co_processing
    qp_tonnes: Mapped[float] = mapped_column(Float)
    cf: Mapped[float] = mapped_column(Float)
    wp: Mapped[float] = mapped_column(Float)
    tonnes: Mapped[float] = mapped_column(Float)

    recycler: Mapped["Collector"] = relationship()


class EPRPurchase(Base):
    """Certificate tonnes transferred recycler -> producer (not tradable between producers)."""

    __tablename__ = "epr_purchases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    producer_id: Mapped[int] = mapped_column(ForeignKey("epr_producers.id"))
    recycler_id: Mapped[int] = mapped_column(ForeignKey("collectors.id"))
    certificate_fy: Mapped[int] = mapped_column(Integer)  # FY of generation (drives expiry)
    tonnes: Mapped[float] = mapped_column(Float)
    price_inr_per_tonne: Mapped[float | None] = mapped_column(Float, nullable=True)
    purchased_on: Mapped[date] = mapped_column(Date)

    producer: Mapped["EPRProducer"] = relationship()
    recycler: Mapped["Collector"] = relationship()


class Shipment(Base):
    """A movement of material between two registered parties (HOWM Form 10 manifest for ULO)."""

    __tablename__ = "shipments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    manifest_no: Mapped[str] = mapped_column(String)
    material: Mapped[str] = mapped_column(String)
    sender_id: Mapped[int] = mapped_column(ForeignKey("collectors.id"))
    receiver_id: Mapped[int] = mapped_column(ForeignKey("collectors.id"))
    lot_id: Mapped[int | None] = mapped_column(ForeignKey("lots.id"), nullable=True)
    vehicle_no: Mapped[str] = mapped_column(String)
    gps_tracked: Mapped[bool] = mapped_column(Boolean, default=True)
    nhwts_registered: Mapped[bool] = mapped_column(Boolean, default=True)  # National Hazardous Waste Tracking System
    spcb_intimated: Mapped[bool] = mapped_column(Boolean, default=True)
    max_container_l: Mapped[float] = mapped_column(Float, default=200.0)
    distance_km: Mapped[float] = mapped_column(Float, default=0.0)
    dispatched_on: Mapped[date] = mapped_column(Date)
    received_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    dispatched_kg: Mapped[float] = mapped_column(Float)
    received_kg: Mapped[float | None] = mapped_column(Float, nullable=True)

    sender: Mapped["Collector"] = relationship(foreign_keys=[sender_id])
    receiver: Mapped["Collector"] = relationship(foreign_keys=[receiver_id])


class ReturnFiling(Base):
    """Quarterly / annual return on the CPCB portal (collection agents, recyclers, producers)."""

    __tablename__ = "return_filings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_name: Mapped[str] = mapped_column(String)
    entity_role: Mapped[str] = mapped_column(String)  # collector | recycler | producer
    period: Mapped[str] = mapped_column(String)  # e.g. "Q1 FY2026-27" or "Annual FY2025-26"
    due_on: Mapped[date] = mapped_column(Date)
    filed_on: Mapped[date | None] = mapped_column(Date, nullable=True)


class LedgerEntry(Base):
    """Append-only, hash-chained log of every custody event (tamper-evident, single-node)."""

    __tablename__ = "ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String)  # collection | shipment | batch | dispatch
    ref_id: Mapped[int] = mapped_column(Integer)
    payload: Mapped[str] = mapped_column(Text)
    prev_hash: Mapped[str] = mapped_column(String)
    hash: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
