from models.user_model import db
from datetime import datetime
from sqlalchemy import Index


class Booking(db.Model):
    """
    Public booking record (client books a slot with an owner).
    This is the source of truth for booked slots (prevents double booking).
    """
    __tablename__ = 'bookings'

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    client_name = db.Column(db.String(200), nullable=False)
    client_email = db.Column(db.String(200), nullable=False)
    client_note = db.Column(db.Text, nullable=True)

    start_time = db.Column(db.DateTime, nullable=False, index=True)
    end_time = db.Column(db.DateTime, nullable=False, index=True)

    provider = db.Column(db.String(20), nullable=False)  # google / microsoft
    calendar_event_id = db.Column(db.String(512), nullable=True)  # provider event id
    meeting_link = db.Column(db.String(500), nullable=True)  # Meet / Teams URL

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    owner = db.relationship('User', backref='bookings')

    __table_args__ = (
        # Helps querying overlaps efficiently
        Index('ix_bookings_owner_time', 'owner_id', 'start_time', 'end_time'),
    )

    def to_public_confirmation(self):
        """Return minimal confirmation payload safe for the client."""
        return {
            'booking_id': self.id,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_minutes': int((self.end_time - self.start_time).total_seconds() // 60),
            'meeting_link': self.meeting_link,
        }


