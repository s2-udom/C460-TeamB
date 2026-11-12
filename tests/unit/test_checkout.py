from datetime import UTC, datetime

import pytest

from app import create_app
from app.extensions import db
from app.models import Event, EventSeat, Seat, Venue


class TestConfig:
    TESTING = True
    SECRET_KEY = "test-secret"
    SQLALCHEMY_DATABASE_URI = "sqlite://"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    METRICS_ENABLED = False
    HOLD_DURATION_MINUTES = 10


@pytest.fixture
def client():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        venue = Venue(name="Test venue", city="Test city")
        seat = Seat(venue=venue, section="A", row_label="A", number=1)
        event = Event(
            venue=venue,
            name="Test event",
            starts_at=datetime.now(UTC),
            status="on_sale",
        )
        event_seat = EventSeat(event=event, seat=seat, price_pence=2500)
        db.session.add_all([venue, seat, event, event_seat])
        db.session.commit()
        event_id = event.id
        event_seat_id = event_seat.id

    yield app.test_client(), event_id, event_seat_id

    with app.app_context():
        db.session.remove()
        db.drop_all()


def test_checkout_turns_active_hold_into_sold_ticket(client):
    http, event_id, event_seat_id = client
    customer = "buyer@example.com"

    held = http.post(
        f"/api/v1/events/{event_id}/holds",
        json={"event_seat_ids": [event_seat_id], "customer": customer},
    )
    assert held.status_code == 201

    checked_out = http.post(
        f"/api/v1/events/{event_id}/checkout",
        json={"event_seat_ids": [event_seat_id], "customer": customer},
    )
    assert checked_out.status_code == 201
    assert checked_out.json["tickets_sold"] == 1

    with http.application.app_context():
        event_seat = db.session.get(EventSeat, event_seat_id)
        assert event_seat.status == "sold"
        assert event_seat.held_by is None
        assert event_seat.hold_expires_at is None
