from app.extensions import db


class Seat(db.Model):
    """A physical seat in a venue. Fixed: the same for every event."""

    __tablename__ = "seats"

    id = db.Column(db.Integer, primary_key=True)
    venue_id = db.Column(db.Integer, db.ForeignKey("venues.id"), nullable=False)
    section = db.Column(db.String(50), nullable=False)
    row_label = db.Column(db.String(10), nullable=False)
    number = db.Column(db.Integer, nullable=False)

    venue = db.relationship("Venue")

    __table_args__ = (
        db.UniqueConstraint(
            "venue_id", "section", "row_label", "number",
            name="uq_seats_venue_section_row_number",
        ),
        db.CheckConstraint("number > 0", name="ck_seats_number_positive"),
    )

    def __repr__(self):
        return f"<Seat {self.section} {self.row_label}{self.number}>"
