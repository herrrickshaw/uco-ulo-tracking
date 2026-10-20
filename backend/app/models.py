from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String
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
    """Base-oil/lubricant producer or importer obliged under the used-oil EPR chapter."""

    __tablename__ = "epr_producers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    fy_start_year: Mapped[int] = mapped_column(Integer)  # FY2024-25 -> 2024
    prior_year_sales_tonnes: Mapped[float] = mapped_column(Float)


class EPRPurchase(Base):
    """EPR certificate tonnes a producer bought from a registered recycler."""

    __tablename__ = "epr_purchases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    producer_id: Mapped[int] = mapped_column(ForeignKey("epr_producers.id"))
    recycler_id: Mapped[int] = mapped_column(ForeignKey("collectors.id"))
    tonnes: Mapped[float] = mapped_column(Float)
    purchased_on: Mapped[date] = mapped_column(Date)

    producer: Mapped["EPRProducer"] = relationship()
    recycler: Mapped["Collector"] = relationship()
