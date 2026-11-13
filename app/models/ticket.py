from app.extensions import db


class Ticket(db.Model):
    """One ticket for one seat. event_seat_id is UNIQUE: the database itself
    refuses a second ticket for the same seat at the same event."""

    __tablename__ = "tickets"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    event_seat_id = db.Column(
        db.Integer, db.ForeignKey("event_seats.id"), nullable=False, unique=True
    )
    code = db.Column(db.String(64), nullable=False, unique=True)

    order = db.relationship("Order", back_populates="tickets")
    event_seat = db.relationship("EventSeat")

    def __repr__(self):
        return f"<Ticket {self.code}>"
