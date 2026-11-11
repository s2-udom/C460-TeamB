"""Seat holds: the core of 'no seat is ever sold twice'.

hold_seats() locks the requested seats with SELECT ... FOR UPDATE SKIP LOCKED,
so two customers can never hold the same seat, even at the same instant.
"""
from datetime import datetime, timedelta, timezone

from flask import current_app
from sqlalchemy import and_, or_

from app.extensions import db
from app.models import EventSeat

MAX_SEATS_PER_HOLD = 6


class SeatsUnavailable(Exception):
    """Raised when one or more requested seats cannot be held."""

    def __init__(self, unavailable_ids):
        self.unavailable_ids = unavailable_ids
        super().__init__(f"Seats unavailable: {unavailable_ids}")


def hold_seats(event_id, event_seat_ids, customer):
    """Hold all requested seats for a customer, or none of them.

    Returns (held_ids, expires_at). Raises SeatsUnavailable if any seat is
    taken, already held, locked by another request, or not part of this event.
    """
    # 1. Current time and when this hold will expire
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=current_app.config["HOLD_DURATION_MINUTES"])

    try:
        # 2. Lock every requested seat that can be held right now.
        #    SKIP LOCKED: seats another request is holding are skipped instantly
        #    instead of making this request wait.
        event_seats = db.session.scalars(
            db.select(EventSeat)
            .where(
                EventSeat.id.in_(event_seat_ids),
                EventSeat.event_id == event_id,
                or_(
                    EventSeat.status == "available",
                    and_(EventSeat.status == "held", EventSeat.hold_expires_at < now),
                ),
            )
            .order_by(EventSeat.id)
            .with_for_update(skip_locked=True)
        ).all()

        # 3. All or nothing: if we didn't get every seat, release the locks
        found_ids = {es.id for es in event_seats}
        unavailable_ids = [sid for sid in event_seat_ids if sid not in found_ids]
        if unavailable_ids:
            db.session.rollback()
            raise SeatsUnavailable(unavailable_ids)

        # 4. Hold each seat
        for es in event_seats:
            es.status = "held"
            es.held_by = customer
            es.hold_expires_at = expires_at

        # 5. Save all holds together (this also releases the row locks)
        db.session.commit()
    except SeatsUnavailable:
        raise
    except Exception:
        db.session.rollback()  # never leave locks or half-written holds behind
        raise

    return sorted(found_ids), expires_at
