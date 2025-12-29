from models.user_model import db
from datetime import datetime
from sqlalchemy import UniqueConstraint


class Availability(db.Model):
    """
    Owner-defined weekly availability (stored in app DB; NOT pushed to Google/Microsoft).

    day_of_week: 0-6 where 0=Monday ... 6=Sunday
    start_time/end_time: time window for the given day (local to owner)
    """
    __tablename__ = 'availability'

    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)

    day_of_week = db.Column(db.Integer, nullable=False)  # 0-6
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = db.relationship('User', backref='availability_rules')

    __table_args__ = (
        UniqueConstraint('owner_id', 'day_of_week', name='uq_availability_owner_day'),
    )

    def to_dict(self):
        return {
            'id': self.id,
            'owner_id': self.owner_id,
            'day_of_week': self.day_of_week,
            'start_time': self.start_time.strftime('%H:%M'),
            'end_time': self.end_time.strftime('%H:%M'),
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


