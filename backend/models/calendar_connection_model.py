from models.user_model import db
from datetime import datetime
import json

class CalendarConnection(db.Model):
    """Model for storing multiple calendar account connections per user"""
    __tablename__ = 'calendar_connections'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Provider info
    provider = db.Column(db.String(20), nullable=False)  # 'google' or 'microsoft'
    provider_account_email = db.Column(db.String(200), nullable=False)  # The email of the connected account
    provider_account_name = db.Column(db.String(200))  # Display name from provider
    
    # OAuth token stored as JSON
    token = db.Column(db.Text, nullable=False)
    
    # Connection status
    is_connected = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)  # For enabling/disabling specific connections
    
    # Calendar info
    calendar_id = db.Column(db.String(100), default='primary')  # Which calendar from this account
    
    # Metadata
    last_synced = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='calendar_connections')
    
    def set_token(self, token_info):
        """Store OAuth token"""
        self.token = json.dumps(token_info)
        self.is_connected = True
    
    def get_token(self):
        """Retrieve OAuth token"""
        if self.token:
            return json.loads(self.token)
        return None
    
    def to_dict(self):
        """Convert connection to dictionary for API response"""
        return {
            'id': self.id,
            'provider': self.provider,
            'provider_account_email': self.provider_account_email,
            'provider_account_name': self.provider_account_name,
            'is_connected': self.is_connected,
            'is_active': self.is_active,
            'calendar_id': self.calendar_id,
            'last_synced': self.last_synced.isoformat() if self.last_synced else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<CalendarConnection {self.provider}:{self.provider_account_email}>'

