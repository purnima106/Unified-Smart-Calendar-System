#!/usr/bin/env python3
"""
Database initialization script
"""

from app import create_app
from models.user_model import db, User
from models.event_model import Event
from sqlalchemy import text

def init_database():
    """Initialize the database with tables"""
    app = create_app()
    
    with app.app_context():
        print("Creating database tables...")
        db.create_all()
        print("Database tables created successfully!")
        
        # Check if we can connect to the database
        try:
            db.session.execute(text('SELECT 1'))
            print("Database connection successful!")
        except Exception as e:
            print(f"Database connection failed: {e}")
            return False
        
        # Check if we have any users
        user_count = User.query.count()
        print(f"Current user count: {user_count}")
        
        return True

if __name__ == '__main__':
    print("Initializing database...")
    success = init_database()
    if success:
        print("Database initialization completed successfully!")
    else:
        print("Database initialization failed!")
