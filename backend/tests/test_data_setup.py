"""
Test Data Setup Script
Creates test data for comprehensive testing
"""
import sys
import os
import json
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Ensure we can import from parent directory
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from app import create_app
from models.user_model import db, User
from models.calendar_connection_model import CalendarConnection
from models.event_model import Event
from config import Config


def create_test_data():
    """Create test data for testing"""
    app = create_app(Config)
    
    with app.app_context():
        print("Creating test data...")
        
        # Create test users
        test_users = [
            {
                'email': 'test.google1@example.com',
                'name': 'Test Google User 1',
                'google_calendar_connected': True
            },
            {
                'email': 'test.google2@example.com',
                'name': 'Test Google User 2',
                'google_calendar_connected': True
            },
            {
                'email': 'test.microsoft1@example.com',
                'name': 'Test Microsoft User 1',
                'microsoft_calendar_connected': True
            },
            {
                'email': 'test.microsoft2@example.com',
                'name': 'Test Microsoft User 2',
                'microsoft_calendar_connected': True
            },
            {
                'email': 'test.multi@example.com',
                'name': 'Test Multi-Provider User',
                'google_calendar_connected': True,
                'microsoft_calendar_connected': True
            }
        ]
        
        created_users = []
        for user_data in test_users:
            user = User.query.filter_by(email=user_data['email']).first()
            if not user:
                user = User(**user_data)
                db.session.add(user)
                created_users.append(user)
                print(f"Created user: {user.email}")
            else:
                created_users.append(user)
                print(f"User already exists: {user.email}")
        
        db.session.commit()
        
        # Create test calendar connections
        print("\nCreating calendar connections...")
        for user in created_users:
            if user.google_calendar_connected:
                conn = CalendarConnection.query.filter_by(
                    user_id=user.id,
                    provider='google',
                    provider_account_email=user.email
                ).first()
                if not conn:
                    # Create dummy token for test data
                    dummy_token = json.dumps({
                        'access_token': 'test_token_google',
                        'refresh_token': 'test_refresh_google',
                        'token_type': 'Bearer',
                        'expires_in': 3600,
                        'expires_at': (datetime.utcnow().timestamp() + 3600)
                    })
                    conn = CalendarConnection(
                        user_id=user.id,
                        provider='google',
                        provider_account_email=user.email,
                        provider_account_name=user.name,
                        calendar_id='primary',
                        token=dummy_token,
                        is_connected=True,
                        is_active=True
                    )
                    db.session.add(conn)
                    print(f"Created Google connection for {user.email}")
            
            if user.microsoft_calendar_connected:
                conn = CalendarConnection.query.filter_by(
                    user_id=user.id,
                    provider='microsoft',
                    provider_account_email=user.email
                ).first()
                if not conn:
                    # Create dummy token for test data
                    dummy_token = json.dumps({
                        'access_token': 'test_token_microsoft',
                        'refresh_token': 'test_refresh_microsoft',
                        'token_type': 'Bearer',
                        'expires_in': 3600,
                        'expires_at': (datetime.utcnow().timestamp() + 3600)
                    })
                    conn = CalendarConnection(
                        user_id=user.id,
                        provider='microsoft',
                        provider_account_email=user.email,
                        provider_account_name=user.name,
                        calendar_id='default',
                        token=dummy_token,
                        is_connected=True,
                        is_active=True
                    )
                    db.session.add(conn)
                    print(f"Created Microsoft connection for {user.email}")
        
        db.session.commit()
        
        # Create test events
        print("\nCreating test events...")
        multi_user = next((u for u in created_users if u.email == 'test.multi@example.com'), None)
        if multi_user:
            # Create overlapping events for conflict testing
            base_time = datetime.now().replace(hour=10, minute=0, second=0, microsecond=0)
            
            # Event 1: Google event
            event1 = Event(
                user_id=multi_user.id,
                title='Google Meeting - Conflict Test',
                description='Test event from Google',
                start_time=base_time,
                end_time=base_time + timedelta(hours=1),
                provider='google',
                provider_event_id=f'google-test-{base_time.timestamp()}',
                calendar_id='primary',
                organizer=multi_user.email,
                has_conflict=False
            )
            db.session.add(event1)
            
            # Event 2: Microsoft event that overlaps
            event2 = Event(
                user_id=multi_user.id,
                title='Microsoft Meeting - Conflict Test',
                description='Test event from Microsoft',
                start_time=base_time + timedelta(minutes=30),  # Overlaps with event1
                end_time=base_time + timedelta(hours=1, minutes=30),
                provider='microsoft',
                provider_event_id=f'microsoft-test-{base_time.timestamp()}',
                calendar_id='default',
                organizer=multi_user.email,
                has_conflict=True,
                conflict_with=f'{event1.id}'
            )
            db.session.add(event2)
            
            # Event 3: Non-conflicting event
            event3 = Event(
                user_id=multi_user.id,
                title='Free Slot Test Event',
                description='Event for free slots testing',
                start_time=base_time + timedelta(days=1, hours=14),
                end_time=base_time + timedelta(days=1, hours=15),
                provider='google',
                provider_event_id=f'google-test-{(base_time + timedelta(days=1)).timestamp()}',
                calendar_id='primary',
                organizer=multi_user.email,
                has_conflict=False
            )
            db.session.add(event3)
            
            print(f"Created 3 test events for {multi_user.email}")
        
        db.session.commit()
        
        print("\n" + "="*60)
        print("Test data setup complete!")
        print("="*60)
        print(f"Created {len(created_users)} test users")
        print(f"Created calendar connections")
        print(f"Created test events")
        print("\nYou can now run the test suite.")


if __name__ == '__main__':
    create_test_data()

