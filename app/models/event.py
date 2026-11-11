from app.extensions import db

EVENT_STATUSES = ("draft", "on_sale", "sold_out", "cancelled")


class Event(db.Model):
    """A show at a venue on a date."""

    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    venue_id = db.Column(db.Integer, db.ForeignKey("venues.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    starts_at = db.Column(db.DateTime(timezone=True), nullable=False)
    status = db.Column(
        db.String(20), nullable=False, default="on_sale", server_default="on_sale"
    )

    venue = db.relationship("Venue")

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('draft', 'on_sale', 'sold_out', 'cancelled')",
            name="ck_events_status",
        ),
    )

    def __repr__(self):
        return f"<Event {self.id} {self.name}>"
