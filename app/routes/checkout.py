"""Test-mode checkout: turn a customer's active hold into paid tickets."""
from datetime import UTC, datetime
from uuid import uuid4

from flask import Blueprint, jsonify, request
from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db
from app.metrics import CHECKOUT_FAILURES, CHECKOUT_REQUESTS, TICKETS_SOLD
from app.models import Event, EventSeat, Order, Ticket

checkout_bp = Blueprint("checkout", __name__, url_prefix="/api/v1")


def _failure(reason, message, status=409):
    CHECKOUT_FAILURES.labels(reason=reason).inc()
    return jsonify({"error": message}), status


def _hold_is_active(hold_expires_at, now):
    """Compare timestamps consistently across PostgreSQL and SQLite tests."""
    if hold_expires_at is None:
        return False
    if hold_expires_at.tzinfo is None:
        hold_expires_at = hold_expires_at.replace(tzinfo=UTC)
    return hold_expires_at > now


@checkout_bp.route("/events/<int:event_id>/checkout", methods=["POST"])
def checkout(event_id):
    """Convert unexpired seats held by the customer into paid tickets."""
    CHECKOUT_REQUESTS.inc()
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _failure("invalid_request", "Request body must be a JSON object", 400)

    event_seat_ids = data.get("event_seat_ids")
    customer = data.get("customer")
    if not isinstance(event_seat_ids, list) or not event_seat_ids:
        return _failure("invalid_request", "event_seat_ids must be a non-empty list", 400)
    if any(type(seat_id) is not int or seat_id < 1 for seat_id in event_seat_ids):
        return _failure("invalid_request", "Every seat ID must be a positive integer", 400)
    if len(event_seat_ids) != len(set(event_seat_ids)):
        return _failure("invalid_request", "Duplicate seat IDs are not allowed", 400)
    if not isinstance(customer, str) or not customer.strip():
        return _failure("invalid_request", "customer must be a non-empty string", 400)
    customer = customer.strip()

    event = db.session.get(Event, event_id)
    if event is None:
        return _failure("event_not_found", "Event not found", 404)
    if event.status != "on_sale":
        return _failure("not_on_sale", f"Event is not on sale (status: {event.status})")

    now = datetime.now(UTC)
    try:
        event_seats = db.session.scalars(
            db.select(EventSeat)
            .where(
                EventSeat.event_id == event_id,
                EventSeat.id.in_(event_seat_ids),
            )
            .order_by(EventSeat.id)
            .with_for_update()
        ).all()

        valid = (
            len(event_seats) == len(event_seat_ids)
            and all(
                seat.status == "held"
                and seat.held_by == customer
                and _hold_is_active(seat.hold_expires_at, now)
                for seat in event_seats
            )
        )
        if not valid:
            db.session.rollback()
            return _failure("hold_unavailable", "One or more seats are no longer held for this customer")

        order = Order(
            event_id=event_id,
            customer_email=customer,
            total_pence=sum(seat.price_pence for seat in event_seats),
            status="paid",
        )
        db.session.add(order)
        db.session.flush()

        for seat in event_seats:
            seat.status = "sold"
            seat.held_by = None
            seat.hold_expires_at = None
            db.session.add(
                Ticket(
                    order_id=order.id,
                    event_seat_id=seat.id,
                    code=f"TKT-{uuid4().hex.upper()}",
                )
            )

        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()
        return _failure("database_error", "Checkout could not be completed", 503)

    TICKETS_SOLD.inc(len(event_seats))
    return jsonify({
        "order_id": order.id,
        "order_ref": f"USH-{order.id:06d}",
        "tickets_sold": len(event_seats),
        "total_pence": order.total_pence,
    }), 201
