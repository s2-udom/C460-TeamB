from datetime import datetime, timezone

from app.extensions import db

ORDER_STATUSES = ("pending", "paid", "cancelled")


def _utcnow():
    return datetime.now(timezone.utc)


class Order(db.Model):
    """A customer's purchase for one event."""

    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    customer_email = db.Column(db.String(255), nullable=False)
    total_pence = db.Column(db.Integer, nullable=False)
    status = db.Column(
        db.String(20), nullable=False, default="pending", server_default="pending"
    )
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utcnow)

    event = db.relationship("Event")
    tickets = db.relationship("Ticket", back_populates="order")

    __table_args__ = (
        db.CheckConstraint(
            "status IN ('pending', 'paid', 'cancelled')", name="ck_orders_status"
        ),
        db.CheckConstraint("total_pence >= 0", name="ck_orders_total_not_negative"),
    )

    def __repr__(self):
        return f"<Order {self.id} {self.status}>"
