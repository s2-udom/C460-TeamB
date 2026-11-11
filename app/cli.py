"""Custom Flask commands. Run with: flask seed  (or: flask seed --reset)."""
from datetime import datetime, timezone

import click

from app.extensions import db
from app.models import Event, EventSeat, Order, Seat, Ticket, Venue

VENUE_NAME = "Riverside Hall"

# Seat layout and prices (in pence) for the demo venue.
SECTIONS = [
    {"name": "Stalls", "rows": ["A", "B", "C", "D"], "price": 4500},
    {"name": "Circle", "rows": ["E", "F"], "price": 3500},
]
SEATS_PER_ROW = 10

EVENTS = [
    {"name": "Low Tide Orchestra", "starts_at": datetime(2026, 11, 20, 19, 30, tzinfo=timezone.utc)},
    {"name": "Night Swim", "starts_at": datetime(2026, 11, 28, 20, 0, tzinfo=timezone.utc)},
]


def _wipe_demo_data():
    """Delete all rows, children first so foreign keys are never broken."""
    for model in (Ticket, Order, EventSeat, Event, Seat, Venue):
        db.session.query(model).delete()


@click.command("seed")
@click.option("--reset", is_flag=True, help="Delete all existing data first, then seed again.")
def seed(reset):
    """Populate the database with a demo venue, seats, events and event seats."""
    try:
        if reset:
            _wipe_demo_data()
            click.echo("Existing data deleted.")

        # 1. Skip if the database has already been seeded
        existing = db.session.scalar(db.select(Venue).filter_by(name=VENUE_NAME))
        if existing:
            click.echo("Already seeded. Use `flask seed --reset` to start fresh.")
            return

        # 2. The venue
        venue = Venue(name=VENUE_NAME, city="London")
        db.session.add(venue)
        db.session.flush()  # sends it to the DB so venue.id exists, without committing

        # 3. The seats (6 rows x 10 = 60)
        seats = []
        for section in SECTIONS:
            for row in section["rows"]:
                for number in range(1, SEATS_PER_ROW + 1):
                    seat = Seat(
                        venue_id=venue.id,
                        section=section["name"],
                        row_label=row,
                        number=number,
                    )
                    db.session.add(seat)
                    seats.append((seat, section["price"]))
        db.session.flush()

        # 4. The events
        events = [Event(venue_id=venue.id, **e) for e in EVENTS]
        db.session.add_all(events)
        db.session.flush()

        # 5. One EventSeat for every seat at every event
        event_seats = [
            EventSeat(event_id=event.id, seat_id=seat.id, price_pence=price)
            for event in events
            for seat, price in seats
        ]
        db.session.add_all(event_seats)

        # 6. Save everything in one transaction
        db.session.commit()
    except Exception:
        db.session.rollback()  # all or nothing: never leave a half-seeded database
        raise

    click.echo(
        f"Seeded 1 venue, {len(seats)} seats, "
        f"{len(events)} events, {len(event_seats)} event seats."
    )
