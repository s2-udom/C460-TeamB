"""POST /api/v1/events/<id>/holds: hold seats for 10 minutes while the customer pays."""
from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Event
from app.services.holds import MAX_SEATS_PER_HOLD, SeatsUnavailable, hold_seats

holds_bp = Blueprint("holds", __name__, url_prefix="/api/v1")


def _bad_request(message):
    return jsonify({"error": message}), 400


@holds_bp.route("/events/<int:event_id>/holds", methods=["POST"])
def create_hold(event_id):
    """Hold the requested seats: 201 on success, 409 if any seat is taken."""
    # 1. Read the JSON body
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _bad_request("Request body must be a JSON object")

    event_seat_ids = data.get("event_seat_ids")
    customer = data.get("customer")

    # 2. Validate event_seat_ids
    if not isinstance(event_seat_ids, list):
        return _bad_request("event_seat_ids must be a list")
    if not 1 <= len(event_seat_ids) <= MAX_SEATS_PER_HOLD:
        return _bad_request(f"You must request between 1 and {MAX_SEATS_PER_HOLD} seats")
    # type() rather than isinstance(): True/False are technically ints in Python
    if any(type(sid) is not int or sid < 1 for sid in event_seat_ids):
        return _bad_request("Every seat ID must be a positive integer")
    if len(event_seat_ids) != len(set(event_seat_ids)):
        return _bad_request("Duplicate seat IDs are not allowed")

    # 3. Validate customer
    if not isinstance(customer, str) or not customer.strip():
        return _bad_request("customer must be a non-empty string")
    customer = customer.strip()
    if len(customer) > 255:
        return _bad_request("customer must be 255 characters or fewer")

    # 4. The event must exist and be on sale
    event = db.session.get(Event, event_id)
    if event is None:
        return jsonify({"error": "Event not found"}), 404
    if event.status != "on_sale":
        return jsonify({"error": f"Event is not on sale (status: {event.status})"}), 409

    # 5. Try to hold the seats
    try:
        held_ids, expires_at = hold_seats(event_id, event_seat_ids, customer)
    except SeatsUnavailable as error:
        return jsonify({
            "error": "Some seats are no longer available",
            "unavailable": error.unavailable_ids,
        }), 409

    return jsonify({
        "event_id": event_id,
        "held": held_ids,
        "customer": customer,
        "expires_at": expires_at.isoformat(),
    }), 201
