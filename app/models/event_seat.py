from app.extensions import db

SEAT_STATUSES = ("available", "held", "sold")


class EventSeat(db.Model):
    """One seat's price and status for one event. Holds and sales happen here."""

    __tablename__ = "event_seats"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    seat_id = db.Column(db.Integer, db.ForeignKey("seats.id"), nullable=False)
    price_pence = db.Column(db.Integer, nullable=False)
    status = db.Column(
        db.String(20), nullable=False, default="available", server_default="available"
    )
    held_by = db.Column(db.String(255), nullable=True)
    hold_expires_at = db.Column(db.DateTime(timezone=True), nullable=True)

    event = db.relationship("Event")
    seat = db.relationship("Seat")

    __table_args__ = (
        db.UniqueConstraint("event_id", "seat_id", name="uq_event_seats_event_seat"),
        db.CheckConstraint(
            "status IN ('available', 'held', 'sold')", name="ck_event_seats_status"
        ),
        db.CheckConstraint("price_pence >= 0", name="ck_event_seats_price_not_negative"),
        # Fast lookups for "all seats for this event with this status".
        db.Index("ix_event_seats_event_status", "event_id", "status"),
    )

    def __repr__(self):
        return f"<EventSeat event={self.event_id} seat={self.seat_id} {self.status}>"
