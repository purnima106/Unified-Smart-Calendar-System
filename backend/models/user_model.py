from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # OAuth tokens stored as JSON
    google_token = db.Column(db.Text)
    microsoft_token = db.Column(db.Text)
    
    # Calendar connections
    google_calendar_connected = db.Column(db.Boolean, default=False)
    microsoft_calendar_connected = db.Column(db.Boolean, default=False)

    # Public booking profile
    # - public_username is used to generate a shareable booking URL: /book/{public_username}
    # - default_slot_duration_minutes controls the default duration shown on the public booking page
    public_username = db.Column(db.String(120), unique=True, nullable=True)
    default_slot_duration_minutes = db.Column(db.Integer, default=30)
    
    # Events relationship
    events = db.relationship('Event', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_google_token(self, token_info):
        """Store Google OAuth token"""
        self.google_token = json.dumps(token_info)
        self.google_calendar_connected = True
        
    def get_google_token(self):
        """Retrieve Google OAuth token"""
        if self.google_token:
            return json.loads(self.google_token)
        return None
        
    def set_microsoft_token(self, token_info):
        """Store Microsoft OAuth token"""
        self.microsoft_token = json.dumps(token_info)
        self.microsoft_calendar_connected = True
        
    def get_microsoft_token(self):
        """Retrieve Microsoft OAuth token"""
        if self.microsoft_token:
            return json.loads(self.microsoft_token)
        return None
    
    def has_connected_calendars(self):
        """Check if user has any connected calendars"""
        return self.google_calendar_connected or self.microsoft_calendar_connected

    def ensure_public_username(self):
        """
        Ensure the user has a public username.
        NOTE: This may be overwritten by a migration/script that handles uniqueness.
        """
        if self.public_username:
            return self.public_username
        # Default to email prefix (safe + deterministic); uniqueness handled elsewhere.
        base = (self.email.split('@')[0] if self.email else f"user{self.id}").strip().lower()
        self.public_username = base
        return self.public_username
    
    def __repr__(self):
        return f'<User {self.email}>'
