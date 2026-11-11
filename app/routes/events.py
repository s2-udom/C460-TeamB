"""Read-only event endpoints: list events and show an event's seat map."""
from datetime import datetime, timezone

from flask import Blueprint, jsonify
from sqlalchemy.orm import contains_eager, joinedload

from app.extensions import db
from app.models import Event, EventSeat, Seat

events_bp = Blueprint("events", __name__, url_prefix="/api/v1")


def _as_utc(value):
    """Return a timezone-aware UTC datetime.

    Postgres gives timezone-aware values back, but SQLite (used in tests)
    can return naive ones, so treat naive values as UTC.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _current_status(event_seat, now):
    """A hold that has run out counts as available, even before the
    clean-up job has reset it in the database."""
    if event_seat.status == "held":
        expires = _as_utc(event_seat.hold_expires_at)
        if expires is not None and expires <= now:
            return "available"
    return event_seat.status


@events_bp.route("/events", methods=["GET"])
def get_events():
    """Return all events, soonest first."""
    events = db.session.scalars(
        db.select(Event)
        .options(joinedload(Event.venue))  # load venues in the same query
        .order_by(Event.starts_at)
    ).all()

    return jsonify([
        {
            "id": event.id,
            "name": event.name,
            "starts_at": _as_utc(event.starts_at).isoformat(),
            "venue": event.venue.name,
            "status": event.status,
        }
        for event in events
    ]), 200


@events_bp.route("/events/<int:event_id>/seats", methods=["GET"])
def get_event_seats(event_id):
    """Return every seat for one event with its price and current status."""
    event = db.session.get(Event, event_id)
    if event is None:
        return jsonify({"error": "Event not found"}), 404

    event_seats = db.session.scalars(
        db.select(EventSeat)
        .join(EventSeat.seat)
        .options(contains_eager(EventSeat.seat))  # reuse the join, no extra query per seat
        .where(EventSeat.event_id == event_id)
        .order_by(Seat.row_label, Seat.number)  # front row first, left to right
    ).all()

    now = datetime.now(timezone.utc)
    seats = []
    summary = {"available": 0, "held": 0, "sold": 0}

    for es in event_seats:
        status = _current_status(es, now)
        summary[status] += 1
        seats.append({
            "event_seat_id": es.id,
            "section": es.seat.section,
            "row": es.seat.row_label,
            "number": es.seat.number,
            "price_pence": es.price_pence,
            "status": status,
        })

    return jsonify({
        "event_id": event.id,
        "event_name": event.name,
        "summary": summary,
        "seats": seats,
    }), 200
