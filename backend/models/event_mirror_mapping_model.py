from models.user_model import db
from datetime import datetime


class EventMirrorMapping(db.Model):
    """Mapping between original provider events and mirrored blocker events."""

    __tablename__ = 'event_mirror_mappings'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    # Original event metadata
    original_provider = db.Column(db.String(20), nullable=False)  # 'google' or 'microsoft'
    original_event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=True)
    original_provider_event_id = db.Column(db.String(512), nullable=False)

    # Mirror event metadata
    mirror_provider = db.Column(db.String(20), nullable=False)  # 'google' or 'microsoft'
    mirror_event_id = db.Column(db.Integer, db.ForeignKey('events.id'), nullable=True)
    mirror_provider_event_id = db.Column(db.String(512), nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Constraints
    __table_args__ = (
        db.UniqueConstraint(
            'original_provider',
            'original_provider_event_id',
            'mirror_provider',
            name='uq_original_mirror_provider_event'
        ),
        db.Index(
            'idx_original_provider_event_id',
            'original_provider',
            'original_provider_event_id'
        ),
        db.Index(
            'idx_mirror_provider_event_id',
            'mirror_provider',
            'mirror_provider_event_id'
        ),
    )

    def __repr__(self):
        return (
            f"<EventMirrorMapping original={self.original_provider}:{self.original_provider_event_id} "
            f"mirror={self.mirror_provider}:{self.mirror_provider_event_id}>"
        )

