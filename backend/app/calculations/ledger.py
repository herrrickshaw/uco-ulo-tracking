"""Hash-chained custody ledger.  Each entry commits to the previous entry's hash and to a
snapshot of the record at logging time, so (a) editing/deleting a log entry breaks the chain and
(b) editing a source row after it was logged is detected.  Single-node and tamper-EVIDENT only:
it does not stop an operator with database access rewriting the whole chain -- anchor the head
hash externally (e.g. publish it daily) for stronger guarantees."""
import hashlib
import json
from datetime import date, datetime

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from ..models import Collection, Dispatch, LedgerEntry, ProcessingBatch, Shipment

KINDS = {"collection": Collection, "shipment": Shipment, "batch": ProcessingBatch, "dispatch": Dispatch}
GENESIS = "0" * 64


def snapshot(row) -> dict:
    out = {}
    for col in inspect(row.__class__).columns:
        v = getattr(row, col.key)
        out[col.key] = v.isoformat() if isinstance(v, (date, datetime)) else v
    return out


def _hash(prev: str, kind: str, ref_id: int, payload: str) -> str:
    return hashlib.sha256(f"{prev}|{kind}|{ref_id}|{payload}".encode()).hexdigest()


def append(db: Session, kind: str, row) -> LedgerEntry:
    last = db.query(LedgerEntry).order_by(LedgerEntry.id.desc()).first()
    prev = last.hash if last else GENESIS
    payload = json.dumps(snapshot(row), sort_keys=True, default=str)
    entry = LedgerEntry(kind=kind, ref_id=row.id, payload=payload, prev_hash=prev, hash=_hash(prev, kind, row.id, payload))
    db.add(entry)
    db.commit()
    return entry


def verify(db: Session) -> dict:
    """Walk the chain; also compare each source row with its logged snapshot."""
    prev, problems, n = GENESIS, [], 0
    for e in db.query(LedgerEntry).order_by(LedgerEntry.id).all():
        n += 1
        if e.prev_hash != prev or e.hash != _hash(e.prev_hash, e.kind, e.ref_id, e.payload):
            problems.append({"entry": e.id, "problem": "chain_broken"})
        prev = e.hash
        row = db.get(KINDS[e.kind], e.ref_id)
        if row is None:
            problems.append({"entry": e.id, "problem": f"{e.kind} {e.ref_id} deleted after logging"})
        elif json.dumps(snapshot(row), sort_keys=True, default=str) != e.payload:
            problems.append({"entry": e.id, "problem": f"{e.kind} {e.ref_id} modified after logging"})
    return {"entries": n, "head_hash": prev, "intact": not problems, "problems": problems}
