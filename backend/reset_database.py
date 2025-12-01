"""
Database Reset Script
Safely clears all users, connections, events, and mappings for a fresh start
WARNING: This will delete all data!
"""
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from config import Config
from models.user_model import db, User
from models.calendar_connection_model import CalendarConnection
from models.event_model import Event
from models.event_mirror_mapping_model import EventMirrorMapping

def reset_database():
    """Reset database - clears all users, connections, events, and mappings"""
    app = create_app(Config)
    
    with app.app_context():
        print("="*60)
        print("DATABASE RESET SCRIPT")
        print("="*60)
        print("\nWARNING: This will delete ALL data from the database!")
        print("This includes:")
        print("  - All users")
        print("  - All calendar connections")
        print("  - All events")
        print("  - All event mirror mappings")
        print("\n" + "="*60)
        
        # Get counts before deletion
        user_count = User.query.count()
        connection_count = CalendarConnection.query.count()
        event_count = Event.query.count()
        mapping_count = EventMirrorMapping.query.count()
        
        print(f"\nCurrent database state:")
        print(f"  Users: {user_count}")
        print(f"  Connections: {connection_count}")
        print(f"  Events: {event_count}")
        print(f"  Mirror Mappings: {mapping_count}")
        
        # Ask for confirmation
        response = input("\nAre you sure you want to delete ALL data? (yes/no): ")
        if response.lower() != 'yes':
            print("Reset cancelled.")
            return
        
        print("\nDeleting data...")
        
        try:
            # Delete in correct order (respecting foreign keys)
            # 1. Delete mirror mappings (references events)
            deleted_mappings = EventMirrorMapping.query.delete()
            print(f"  Deleted {deleted_mappings} mirror mappings")
            
            # 2. Delete events (references users and connections)
            deleted_events = Event.query.delete()
            print(f"  Deleted {deleted_events} events")
            
            # 3. Delete calendar connections (references users)
            deleted_connections = CalendarConnection.query.delete()
            print(f"  Deleted {deleted_connections} connections")
            
            # 4. Delete users
            deleted_users = User.query.delete()
            print(f"  Deleted {deleted_users} users")
            
            # Commit all deletions
            db.session.commit()
            
            print("\n" + "="*60)
            print("DATABASE RESET COMPLETE")
            print("="*60)
            print("\nAll data has been cleared.")
            print("\nNext steps:")
            print("1. Restart your backend server")
            print("2. Log in with your accounts again")
            print("3. Sync your calendars")
            print("4. Verify all events appear correctly")
            
        except Exception as e:
            print(f"\nError during reset: {e}")
            db.session.rollback()
            import traceback
            traceback.print_exc()
            print("\nReset failed. Database may be in an inconsistent state.")
            print("You may need to manually fix the database.")


if __name__ == '__main__':
    reset_database()

