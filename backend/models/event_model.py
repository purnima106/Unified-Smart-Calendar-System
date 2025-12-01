from models.user_model import db
from datetime import datetime
import json

class Event(db.Model):
    __tablename__ = 'events'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Event details
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(200))
    
    # Time details
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    all_day = db.Column(db.Boolean, default=False)
    
    # Calendar provider info
    provider = db.Column(db.String(20), nullable=False)  # 'google' or 'microsoft'
    provider_event_id = db.Column(db.String(512), unique=True)  # Increased length for multi-account support (email:event_id)
    calendar_id = db.Column(db.String(100))  # Calendar ID from provider
    
    # Event metadata
    attendees = db.Column(db.Text)  # JSON array of attendees
    organizer = db.Column(db.String(200))
    color = db.Column(db.String(7))  # Hex color code
    meet_link = db.Column(db.String(500))  # Google Meet or video conference link
    
    # Conflict detection
    has_conflict = db.Column(db.Boolean, default=False)
    conflict_with = db.Column(db.Text)  # JSON array of conflicting event IDs
    
    # Sync info
    last_synced = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_attendees(self, attendees_list):
        """Store attendees as JSON"""
        self.attendees = json.dumps(attendees_list)
    
    def get_attendees(self):
        """Retrieve attendees from JSON"""
        if self.attendees:
            return json.loads(self.attendees)
        return []
    
    def set_conflict_with(self, conflict_ids):
        """Store conflicting event IDs as JSON"""
        self.conflict_with = json.dumps(conflict_ids)
        self.has_conflict = len(conflict_ids) > 0
    
    def get_conflict_with(self):
        """Retrieve conflicting event IDs from JSON"""
        if self.conflict_with:
            return json.loads(self.conflict_with)
        return []
    
    def to_dict(self):
        """Convert event to dictionary for API response"""
        return {
            'id': self.id,
            'user_id': self.user_id,  # Add user_id to response
            'title': self.title,
            'description': self.description,
            'location': self.location,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'all_day': self.all_day,
            'provider': self.provider,
            'provider_event_id': self.provider_event_id,
            'calendar_id': self.calendar_id,
            'attendees': self.get_attendees(),
            'organizer': self.organizer or '',  # Ensure organizer is always a string
            'color': self.color,
            'has_conflict': self.has_conflict,
            'conflict_with': self.get_conflict_with(),
            'last_synced': self.last_synced.isoformat() if self.last_synced else None,
            'meet_link': self.meet_link or None
        }
    
    def __repr__(self):
        return f'<Event {self.title} ({self.provider})>'
