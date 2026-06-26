"""Persist SignalRow list as SignalSnapshot ORM rows.

Default behavior: skip rows whose (date, etf_code) already exists.
With overwrite=True: update existing rows in place.
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.signal_snapshot import SignalSnapshot
from app.signals.compute import SignalRow


def save_signal_snapshot(
    session: Session,
    signal_date: date,
    rows: list[SignalRow],
    *,
    overwrite: bool = False,
) -> list[SignalSnapshot]:
    """Write SignalSnapshot rows for the given date.

    - rows=[] → commit (no-op) and return [].
    - overwrite=False (default): skip codes that already have a snapshot for
      `signal_date`; only insert new codes.
    - overwrite=True: update existing rows' score / rank / action; insert
      new codes.

    Returns the list of SignalSnapshot rows that were inserted or updated.
    """
    if not rows:
        session.commit()
        return []

    codes = [r.etf_code for r in rows]
    existing = session.execute(
        select(SignalSnapshot).where(
            SignalSnapshot.date == signal_date,
            SignalSnapshot.etf_code.in_(codes),
        )
    ).scalars().all()
    existing_by_code = {row.etf_code: row for row in existing}

    written: list[SignalSnapshot] = []
    for row in rows:
        if row.etf_code in existing_by_code:
            if not overwrite:
                continue
            existing_row = existing_by_code[row.etf_code]
            existing_row.momentum_score = row.momentum_score
            existing_row.rank = row.rank
            existing_row.action = row.action
            written.append(existing_row)
        else:
            new_row = SignalSnapshot(
                date=signal_date,
                etf_code=row.etf_code,
                momentum_score=row.momentum_score,
                rank=row.rank,
                action=row.action,
            )
            session.add(new_row)
            written.append(new_row)

    session.commit()
    return written


__all__ = ["save_signal_snapshot"]
