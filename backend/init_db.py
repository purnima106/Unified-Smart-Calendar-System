#!/usr/bin/env python3
"""
Database initialization script
"""

import sys
import time
from app import create_app
from models import db  # ensures all models are imported/registered (incl. new booking tables)
from models.user_model import User
from sqlalchemy import text

def init_database(max_retries=5, retry_delay=2):
    """Initialize the database with tables"""
    app = create_app()
    
    with app.app_context():
        # Retry database connection (useful for Docker when DB might not be ready)
        for attempt in range(max_retries):
            try:
                print(f"Attempting to connect to database (attempt {attempt + 1}/{max_retries})...")
                db.session.execute(text('SELECT 1'))
                print("Database connection successful!")
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"Database connection failed: {e}")
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    print(f"Database connection failed after {max_retries} attempts: {e}")
                    return False
        
        # Create database tables
        try:
            print("Creating database tables...")
            db.create_all()
            print("Database tables created successfully!")
        except Exception as e:
            print(f"Error creating database tables: {e}")
            return False
        
        # Verify tables were created
        try:
            user_count = User.query.count()
            print(f"Current user count: {user_count}")
        except Exception as e:
            print(f"Warning: Could not query users (tables may not exist): {e}")
            return False
        
        return True

if __name__ == '__main__':
    print("Initializing database...")
    success = init_database()
    if success:
        print("Database initialization completed successfully!")
        sys.exit(0)
    else:
        print("Database initialization failed!")
        sys.exit(1)
