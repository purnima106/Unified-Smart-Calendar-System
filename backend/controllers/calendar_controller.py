from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from models.event_model import Event, db
from services.google_service import GoogleCalendarService
from services.microsoft_service import MicrosoftCalendarService
from services.conflict_service import ConflictDetectionService
from services.bidirectional_sync_service import BidirectionalSyncService
from services.event_creation_service import EventCreationService
from services.meeting_detection_service import MeetingDetectionService

calendar_bp = Blueprint('calendar', __name__)

@calendar_bp.route('/debug/microsoft')
def debug_microsoft_sync():
    """Debug endpoint to diagnose Microsoft sync issues"""
    from models.calendar_connection_model import CalendarConnection
    from models.user_model import User
    
    debug_info = {
        'status': 'debug',
        'steps': []
    }
    
    try:
        # Step 1: Check Microsoft connections
        ms_connections = CalendarConnection.query.filter_by(
            provider='microsoft',
            is_active=True,
            is_connected=True
        ).all()
        
        debug_info['steps'].append({
            'step': 1,
            'name': 'Check connections',
            'result': f'Found {len(ms_connections)} Microsoft connection(s)',
            'connections': [{
                'id': c.id,
                'email': c.provider_account_email,
                'user_id': c.user_id,
                'has_token': c.get_token() is not None,
                'last_synced': str(c.last_synced) if c.last_synced else None
            } for c in ms_connections]
        })
        
        if not ms_connections:
            debug_info['error'] = 'No Microsoft connections found'
            return jsonify(debug_info)
        
        # Step 2: Check token structure
        conn = ms_connections[0]
        token = conn.get_token()
        
        token_debug = {
            'has_token': token is not None,
            'keys': list(token.keys()) if token else [],
            'has_access_token': 'access_token' in token if token else False,
            'has_refresh_token': 'refresh_token' in token if token else False,
            'expires_at': token.get('expires_at') if token else None,
            'is_expired': datetime.utcnow().timestamp() > token.get('expires_at', 0) if token else True
        }
        
        debug_info['steps'].append({
            'step': 2,
            'name': 'Check token',
            'result': 'Token found' if token else 'No token',
            'token_info': token_debug
        })
        
        if not token:
            debug_info['error'] = 'No token found in connection'
            return jsonify(debug_info)
        
        # Step 3: Try to create Microsoft service
        try:
            ms_service = MicrosoftCalendarService()
            debug_info['steps'].append({
                'step': 3,
                'name': 'Create Microsoft service',
                'result': 'Success'
            })
        except Exception as e:
            debug_info['steps'].append({
                'step': 3,
                'name': 'Create Microsoft service',
                'result': f'Failed: {str(e)}'
            })
            debug_info['error'] = f'Failed to create Microsoft service: {str(e)}'
            return jsonify(debug_info)
        
        # Step 4: Try to get graph client
        try:
            client = ms_service.get_graph_client_for_connection(conn)
            debug_info['steps'].append({
                'step': 4,
                'name': 'Get Graph client',
                'result': 'Success'
            })
        except Exception as e:
            import traceback
            debug_info['steps'].append({
                'step': 4,
                'name': 'Get Graph client',
                'result': f'Failed: {str(e)}',
                'traceback': traceback.format_exc()
            })
            debug_info['error'] = f'Failed to get Graph client: {str(e)}'
            return jsonify(debug_info)
        
        # Step 5: Try to fetch events from API
        try:
            import pytz
            ist_tz = pytz.timezone('Asia/Kolkata')
            now = datetime.now(ist_tz)
            start_date = (now - timedelta(days=30)).isoformat()
            end_date = (now + timedelta(days=30)).isoformat()
            
            events_data = client.get_calendar_events(start_date, end_date)
            events = events_data.get('value', [])
            
            debug_info['steps'].append({
                'step': 5,
                'name': 'Fetch events from API',
                'result': f'Got {len(events)} events',
                'sample_events': [{
                    'subject': e.get('subject', 'No Title'),
                    'start': e.get('start', {}),
                    'isOnlineMeeting': e.get('isOnlineMeeting'),
                    'attendees_count': len(e.get('attendees', [])),
                    'is_meeting_detected': MeetingDetectionService.is_microsoft_real_meeting(event_data=e)
                } for e in events[:5]]
            })
        except Exception as e:
            import traceback
            debug_info['steps'].append({
                'step': 5,
                'name': 'Fetch events from API',
                'result': f'Failed: {str(e)}',
                'traceback': traceback.format_exc()
            })
            debug_info['error'] = f'Failed to fetch events: {str(e)}'
            return jsonify(debug_info)
        
        # Step 6: Check database for Microsoft events
        db_events = Event.query.filter_by(
            user_id=conn.user_id,
            provider='microsoft'
        ).all()
        
        debug_info['steps'].append({
            'step': 6,
            'name': 'Check database',
            'result': f'Found {len(db_events)} Microsoft events in database',
            'sample_events': [{
                'id': e.id,
                'title': e.title,
                'provider_event_id': e.provider_event_id[:50] + '...' if e.provider_event_id and len(e.provider_event_id) > 50 else e.provider_event_id
            } for e in db_events[:5]]
        })
        
        debug_info['summary'] = {
            'api_events': len(events),
            'db_events': len(db_events),
            'connection_email': conn.provider_account_email
        }
        
        return jsonify(debug_info)
        
    except Exception as e:
        import traceback
        debug_info['error'] = str(e)
        debug_info['traceback'] = traceback.format_exc()
        return jsonify(debug_info)

@calendar_bp.route('/debug/microsoft/sync')
def debug_microsoft_force_sync():
    """Force sync Microsoft events and return detailed results"""
    from models.calendar_connection_model import CalendarConnection
    from flask_login import current_user
    
    result = {
        'status': 'starting',
        'steps': []
    }
    
    try:
        # Get Microsoft connection for user 2 (or first available)
        conn = CalendarConnection.query.filter_by(
            provider='microsoft',
            is_active=True,
            is_connected=True,
            provider_account_email='p.nahata@cloudextel.com'
        ).first()
        
        if not conn:
            conn = CalendarConnection.query.filter_by(
                provider='microsoft',
                is_active=True,
                is_connected=True
            ).first()
        
        if not conn:
            result['error'] = 'No Microsoft connection found'
            return jsonify(result)
        
        result['steps'].append({
            'step': 1,
            'name': 'Found connection',
            'email': conn.provider_account_email,
            'user_id': conn.user_id,
            'last_synced_before': str(conn.last_synced)
        })
        
        # Run sync
        ms_service = MicrosoftCalendarService()
        
        try:
            synced_count = ms_service.sync_events_for_connection(conn, days_back=30, days_forward=30)
            result['steps'].append({
                'step': 2,
                'name': 'Sync completed',
                'synced_count': synced_count
            })
        except Exception as e:
            import traceback
            result['steps'].append({
                'step': 2,
                'name': 'Sync failed',
                'error': str(e),
                'traceback': traceback.format_exc()
            })
            result['error'] = str(e)
            return jsonify(result)
        
        # Check database after sync
        db.session.refresh(conn)
        
        db_events = Event.query.filter_by(
            user_id=conn.user_id,
            provider='microsoft'
        ).all()
        
        # Count real events vs mirror events
        real_events = [e for e in db_events if not e.title.startswith('[Mirror]')]
        mirror_events = [e for e in db_events if e.title.startswith('[Mirror]')]
        
        result['steps'].append({
            'step': 3,
            'name': 'Check database after sync',
            'total_events': len(db_events),
            'real_events': len(real_events),
            'mirror_events': len(mirror_events),
            'last_synced_after': str(conn.last_synced),
            'sample_real_events': [{
                'id': e.id,
                'title': e.title,
                'start_time': str(e.start_time),
                'provider_event_id': e.provider_event_id[:60] + '...' if len(e.provider_event_id or '') > 60 else e.provider_event_id
            } for e in real_events[:5]]
        })
        
        result['status'] = 'success'
        result['summary'] = {
            'synced_count': synced_count,
            'real_events_in_db': len(real_events),
            'mirror_events_in_db': len(mirror_events),
            'last_synced': str(conn.last_synced)
        }
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        result['error'] = str(e)
        result['traceback'] = traceback.format_exc()
        return jsonify(result)

@calendar_bp.route('/test')
def test_calendar():
    """Test endpoint for calendar API"""
    try:
        # Get basic stats
        total_events = Event.query.count()
        total_users = db.session.query(db.func.count(Event.user_id.distinct())).scalar()
        
        # Get events by provider
        google_events = Event.query.filter_by(provider='google').count()
        microsoft_events = Event.query.filter_by(provider='microsoft').count()
        
        return jsonify({
            'status': 'success',
            'message': 'Calendar API is working',
            'stats': {
                'total_events': total_events,
                'total_users': total_users,
                'google_events': google_events,
                'microsoft_events': microsoft_events
            },
            'timestamp': datetime.utcnow().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def get_test_user():
    """Get or create test user for development"""
    from models.user_model import User
    
    user = User.query.first()
    if not user:
        user = User(email="test@example.com", name="Test User")
        db.session.add(user)
        db.session.commit()
        print(f"Created test user: {user.email}")
    return user

def create_sample_events(user):
    """Create sample events for testing the calendar display"""
    from datetime import datetime, timedelta
    import pytz
    
    # Check if sample events already exist
    existing_events = Event.query.filter_by(user_id=user.id).count()
    if existing_events > 0:
        print(f"User already has {existing_events} events, skipping sample creation")
        return Event.query.filter_by(user_id=user.id).all()
    
    sample_events = []
    
    # Get current date in IST
    ist_tz = pytz.timezone('Asia/Kolkata')
    now = datetime.now(ist_tz)
    
    # Sample events for the next 30 days - NO INTENTIONAL CONFLICTS
    events_data = [
        {
            'title': 'Team Meeting',
            'description': 'Weekly team sync meeting',
            'location': 'Conference Room A',
            'start_time': now + timedelta(days=1, hours=10),
            'end_time': now + timedelta(days=1, hours=11),
            'provider': 'google',
            'all_day': False
        },
        {
            'title': 'Client Presentation',
            'description': 'Present quarterly results to client',
            'location': 'Virtual Meeting',
            'start_time': now + timedelta(days=2, hours=14),
            'end_time': now + timedelta(days=2, hours=15, minutes=30),
            'provider': 'microsoft',
            'all_day': False
        },
        {
            'title': 'Lunch with Colleague',
            'description': 'Catch up over lunch',
            'location': 'Office Cafeteria',
            'start_time': now + timedelta(days=3, hours=12),
            'end_time': now + timedelta(days=3, hours=13),
            'provider': 'google',
            'all_day': False
        },
        {
            'title': 'Project Deadline',
            'description': 'Submit final project deliverables',
            'location': 'Office',
            'start_time': now + timedelta(days=5),
            'end_time': now + timedelta(days=5),
            'provider': 'microsoft',
            'all_day': True
        },
        {
            'title': 'Code Review',
            'description': 'Review pull requests with team',
            'location': 'Meeting Room B',
            'start_time': now + timedelta(days=7, hours=16),
            'end_time': now + timedelta(days=7, hours=17),
            'provider': 'google',
            'all_day': False
        },
        {
            'title': 'Google Event 1',
            'description': 'Sample Google calendar event',
            'location': 'Room 1',
            'start_time': now + timedelta(days=10, hours=9),
            'end_time': now + timedelta(days=10, hours=10),
            'provider': 'google',
            'all_day': False
        },
        {
            'title': 'Microsoft Event 1',
            'description': 'Sample Microsoft calendar event',
            'location': 'Room 2',
            'start_time': now + timedelta(days=10, hours=14),  # Changed from 9:30 to 14:00 to avoid conflict
            'end_time': now + timedelta(days=10, hours=15),    # Changed from 10:30 to 15:00
            'provider': 'microsoft',
            'all_day': False
        },
        {
            'title': 'Strategy Meeting',
            'description': 'Quarterly strategy planning',
            'location': 'Board Room',
            'start_time': now + timedelta(days=12, hours=11),
            'end_time': now + timedelta(days=12, hours=12, minutes=30),
            'provider': 'google',
            'all_day': False
        },
        {
            'title': 'Product Demo',
            'description': 'Demo new features to stakeholders',
            'location': 'Virtual Meeting',
            'start_time': now + timedelta(days=15, hours=13),
            'end_time': now + timedelta(days=15, hours=14),
            'provider': 'microsoft',
            'all_day': False
        }
    ]
    
    for event_data in events_data:
        event = Event(
            user_id=user.id,
            title=event_data['title'],
            description=event_data['description'],
            location=event_data['location'],
            start_time=event_data['start_time'].replace(tzinfo=None),  # Store as naive datetime
            end_time=event_data['end_time'].replace(tzinfo=None),
            all_day=event_data['all_day'],
            provider=event_data['provider'],
            provider_event_id=f"sample_{len(sample_events)}",
            calendar_id='primary',
            organizer=user.email,
            last_synced=now.replace(tzinfo=None)
        )
        
        # Set attendees for some events
        if event_data['title'] in ['Team Meeting', 'Client Presentation']:
            event.set_attendees([
                {'email': 'colleague1@example.com', 'name': 'John Doe'},
                {'email': 'colleague2@example.com', 'name': 'Jane Smith'}
            ])
        
        sample_events.append(event)
        db.session.add(event)
    
    try:
        db.session.commit()
        print(f"Created {len(sample_events)} sample events for user {user.email}")
        return sample_events
    except Exception as e:
        db.session.rollback()
        print(f"Error creating sample events: {e}")
        return []

@calendar_bp.route('/events', methods=['GET'])
@login_required
def get_events():
    """Get events from connected accounts for the current user (unified calendar view)"""
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        provider = request.args.get('provider')  # 'google', 'microsoft', or None for all
        
        user_id = current_user.id
        print(f"Getting events for user {user_id} from connected accounts")
        print(f"Query params: start_date={start_date}, end_date={end_date}, provider={provider}")
        
        # Get all active connections for this user
        from models.calendar_connection_model import CalendarConnection
        connections = CalendarConnection.query.filter_by(
            user_id=user_id,
            is_active=True,
            is_connected=True
        ).all()
        
        # Get connected account emails
        connected_emails = [conn.provider_account_email for conn in connections]
        connected_providers = list(set([conn.provider for conn in connections]))  # Unique providers
        
        print(f"Found {len(connections)} active connections for user {user_id}")
        for conn in connections:
            print(f"  - {conn.provider}: {conn.provider_account_email}")
        
        # Build a simpler query for local/dev use:
        # - Show all non-[Mirror] events belonging to this user
        # - Respect the requested date range and provider, but DO NOT
        #   aggressively filter by CalendarConnection metadata.
        # This keeps behaviour consistent with the summary you see on the dashboard.
        query = Event.query.filter(Event.user_id == user_id)
        query = query.filter(~Event.title.ilike('[mirror]%'))
 
        # Debug: Check all events for this user before date/provider filtering
        all_user_events = Event.query.filter(Event.user_id == user_id).all()
        print(f"DEBUG: Total events for user {user_id} (before date/provider filtering): {len(all_user_events)}")
        for e in all_user_events[:5]:
            print(f"  - {e.provider}: {e.title} (organizer: {e.organizer or 'None'}, provider_event_id: {e.provider_event_id or 'None'})")
        
        if start_date:
            start_datetime = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(Event.start_time >= start_datetime)
        
        if end_date:
            end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(Event.end_time <= end_datetime)
        
        if provider:
            query = query.filter(Event.provider == provider)
        
        # Order by start time
        events = query.order_by(Event.start_time).all()
        
        print(f"Found {len(events)} events from connected accounts (after filtering)")
        
        # Debug: Show which filter conditions matched
        if len(events) == 0 and len(all_user_events) > 0:
            print("WARNING: Events exist for user but didn't match filter conditions!")
            print("Checking why events didn't match...")
            for e in all_user_events:
                matched = False
                reasons = []
                if e.user_id == user_id and e.provider in connected_providers:
                    matched = True
                    reasons.append("user_id + provider match")
                if e.organizer and e.organizer in connected_emails:
                    matched = True
                    reasons.append("organizer match")
                if e.provider_event_id and any(e.provider_event_id.startswith(f"{email}:") for email in connected_emails):
                    matched = True
                    reasons.append("provider_event_id match")
                if not matched:
                    print(f"  ❌ Event '{e.title}' didn't match:")
                    print(f"     user_id: {e.user_id} (expected: {user_id})")
                    print(f"     provider: {e.provider} (expected: {connected_providers})")
                    print(f"     organizer: {e.organizer} (expected one of: {connected_emails})")
                    print(f"     provider_event_id: {e.provider_event_id}")
        
        # If no events found, return empty array
        if len(events) == 0:
            print("No events found for connected accounts")
            return jsonify({
                'events': [],
                'count': 0,
                'status': 'success'
            })
        
        # Group events by provider for debugging
        events_by_provider = {}
        for event in events:
            provider = event.provider or 'unknown'
            if provider not in events_by_provider:
                events_by_provider[provider] = []
            events_by_provider[provider].append(event)
        
        print(f"Events by provider:")
        for provider, provider_events in events_by_provider.items():
            print(f"  {provider}: {len(provider_events)} events")
            for event in provider_events:
                print(f"    - {event.title} (organizer: {event.organizer}) at {event.start_time}")
        
        # Deduplicate events based on title, start time, end time, AND provider
        # This prevents the same meeting from appearing twice when synced from different providers
        # BUT allows different providers to have separate meetings with the same title/time
        unique_events = []
        seen_events = set()
        
        # Sort events by creation time to prioritize older events
        events.sort(key=lambda x: x.created_at)
        
        for event in events:
            # Create a unique key based on title, start time, end time, AND provider
            # This ensures Google and Microsoft events with same title/time are both shown
            # Normalize the title to handle case differences and extra spaces
            normalized_title = event.title.lower().strip()
            
            # Create a more flexible key that allows for small time differences
            # (in case of timezone conversion issues)
            start_time_str = event.start_time.strftime('%Y-%m-%d %H:%M')
            end_time_str = event.end_time.strftime('%Y-%m-%d %H:%M')
            
            # Include provider in the key to allow same title/time from different providers
            provider_event_identifier = event.provider_event_id or event.organizer or f"event-{event.id}"
            event_key = (normalized_title, start_time_str, end_time_str, event.provider, provider_event_identifier)
            
            if event_key not in seen_events:
                seen_events.add(event_key)
                unique_events.append(event)
                print(f"Added unique event: {event.title} ({event.provider}) at {event.start_time}")
            else:
                print(f"Skipped duplicate event: {event.title} ({event.provider}) at {event.start_time}")
                # Log the duplicate for debugging
                existing_event = next(e for e in unique_events if (
                    e.title.lower().strip() == normalized_title and
                    e.start_time.strftime('%Y-%m-%d %H:%M') == start_time_str and
                    e.end_time.strftime('%Y-%m-%d %H:%M') == end_time_str and
                    e.provider == event.provider
                ))
                print(f"  - Conflicts with: {existing_event.title} ({existing_event.provider}) at {existing_event.start_time}")
        
        print(f"After deduplication: {len(unique_events)} unique events")
        
        # Convert to dictionary format
        events_data = [event.to_dict() for event in unique_events]
        
        print(f"Returning {len(events_data)} events")
        
        return jsonify({
            'events': events_data,
            'count': len(events_data),
            'status': 'success'
        })
        
    except Exception as e:
        print(f"Error getting events: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@calendar_bp.route('/events/<int:event_id>', methods=['GET'])
def get_event(event_id):
    """Get a specific event from any user"""
    try:
        event = Event.query.filter_by(id=event_id).first()
        
        if not event:
            return jsonify({'error': 'Event not found'}), 404
        
        return jsonify(event.to_dict()), 200
    except Exception as e:
        print(f"Error getting event {event_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

@calendar_bp.route('/sync/google', methods=['POST'])
def sync_google_events():
    """Sync events from Google Calendar for all Google-connected accounts (supports multiple accounts)"""
    try:
        from models.calendar_connection_model import CalendarConnection
        from models.user_model import User
        
        # Get all active Google calendar connections
        google_connections = CalendarConnection.query.filter_by(
            provider='google',
            is_active=True,
            is_connected=True
        ).all()
        
        # Fallback to legacy User model if no connections found
        if not google_connections:
            google_users = User.query.filter_by(google_calendar_connected=True).all()
            if not google_users:
                return jsonify({
                    'message': 'No Google-connected accounts found',
                    'synced_count': 0,
                    'conflicts_detected': 0,
                    'accounts_synced': 0
                })
            
            # Use legacy sync for backward compatibility
            total_synced = 0
            google_service = GoogleCalendarService()
            
            for user in google_users:
                try:
                    print(f"Syncing Google calendar for user: {user.email} (legacy)")
                    synced_count = google_service.sync_events(user, days_back=30, days_forward=30)
                    total_synced += synced_count
                    print(f"Synced {synced_count} events for {user.email}")
                except Exception as e:
                    print(f"Error syncing Google calendar for {user.email}: {e}")
                    continue
            
            return jsonify({
                'message': f'Google Calendar sync completed for {len(google_users)} users (legacy)',
                'synced_count': total_synced,
                'accounts_synced': len(google_users),
                'conflicts_detected': 0
            })
        
        # Sync all Google connections
        total_synced = 0
        accounts_synced = 0
        google_service = GoogleCalendarService()
        sync_results = []
        all_user_ids = set()  # Track all user IDs for conflict detection
        
        for connection in google_connections:
            try:
                print(f"Syncing Google calendar for account: {connection.provider_account_email}")
                synced_count = google_service.sync_events_for_connection(connection, days_back=30, days_forward=30)
                total_synced += synced_count
                accounts_synced += 1
                all_user_ids.add(connection.user_id)  # Add user ID for conflict detection
                sync_results.append({
                    'account_email': connection.provider_account_email,
                    'account_name': connection.provider_account_name,
                    'synced_count': synced_count
                })
                print(f"Synced {synced_count} events for {connection.provider_account_email}")
            except Exception as e:
                print(f"Error syncing Google calendar for {connection.provider_account_email}: {e}")
                sync_results.append({
                    'account_email': connection.provider_account_email,
                    'account_name': connection.provider_account_name,
                    'error': str(e)
                })
                continue
        
        # Automatically detect conflicts after sync for all users
        conflicts_detected = 0
        if all_user_ids:
            try:
                from services.conflict_service import ConflictDetectionService
                conflict_service = ConflictDetectionService()
                for user_id in all_user_ids:
                    print(f"Detecting conflicts for user {user_id} after sync...")
                    user_conflicts = conflict_service.detect_conflicts(user_id)
                    conflicts_detected += len(user_conflicts)
                    print(f"Detected {len(user_conflicts)} conflicts for user {user_id}")
            except Exception as e:
                print(f"Error detecting conflicts after sync: {e}")
        
        return jsonify({
            'message': f'Google Calendar sync completed for {accounts_synced} account(s)',
            'synced_count': total_synced,
            'accounts_synced': accounts_synced,
            'total_accounts': len(google_connections),
            'sync_results': sync_results,
            'conflicts_detected': conflicts_detected
        })
        
    except Exception as e:
        print(f"Google sync error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@calendar_bp.route('/sync/microsoft', methods=['POST'])
def sync_microsoft_events():
    """Sync events from Microsoft Calendar for all Microsoft-connected accounts (supports multiple accounts)"""
    try:
        from models.calendar_connection_model import CalendarConnection
        from models.user_model import User
        
        # Get all active Microsoft calendar connections
        microsoft_connections = CalendarConnection.query.filter_by(
            provider='microsoft',
            is_active=True,
            is_connected=True
        ).all()
        
        # Fallback to legacy User model if no connections found
        if not microsoft_connections:
            microsoft_users = User.query.filter_by(microsoft_calendar_connected=True).all()
            if not microsoft_users:
                return jsonify({
                    'message': 'No Microsoft-connected accounts found',
                    'synced_count': 0,
                    'conflicts_detected': 0,
                    'accounts_synced': 0
                })
            
            # Use legacy sync for backward compatibility
            total_synced = 0
            microsoft_service = MicrosoftCalendarService()
            
            for user in microsoft_users:
                try:
                    print(f"Syncing Microsoft calendar for user: {user.email} (legacy)")
                    synced_count = microsoft_service.sync_events(user, days_back=30, days_forward=30)
                    total_synced += synced_count
                    print(f"Synced {synced_count} events for {user.email}")
                except Exception as e:
                    print(f"Error syncing Microsoft calendar for {user.email}: {e}")
                    continue
            
            return jsonify({
                'message': f'Microsoft Calendar sync completed for {len(microsoft_users)} users (legacy)',
                'synced_count': total_synced,
                'accounts_synced': len(microsoft_users),
                'conflicts_detected': 0
            })
        
        # Sync using CalendarConnection model
        total_synced = 0
        accounts_synced = 0
        all_user_ids = set()
        microsoft_service = MicrosoftCalendarService()
        sync_results = []
        
        for connection in microsoft_connections:
            try:
                print(f"Syncing Microsoft calendar for account: {connection.provider_account_email}")
                user = User.query.get(connection.user_id)
                if not user:
                    print(f"User {connection.user_id} not found for connection {connection.id}")
                    continue
                
                all_user_ids.add(user.id)
                
                # Use connection-based sync (same as Google)
                synced_count = microsoft_service.sync_events_for_connection(connection, days_back=30, days_forward=30)
                total_synced += synced_count
                accounts_synced += 1
                
                print(f"Synced {synced_count} events for {connection.provider_account_email}")
                sync_results.append({
                    'account_email': connection.provider_account_email,
                    'account_name': connection.provider_account_name,
                    'synced_count': synced_count
                })
            except Exception as e:
                print(f"Error syncing Microsoft calendar for {connection.provider_account_email}: {e}")
                import traceback
                traceback.print_exc()
                sync_results.append({
                    'account_email': connection.provider_account_email,
                    'account_name': connection.provider_account_name,
                    'error': str(e)
                })
                continue
        
        # Automatically detect conflicts after sync for all users
        conflicts_detected = 0
        if all_user_ids:
            try:
                from services.conflict_service import ConflictDetectionService
                conflict_service = ConflictDetectionService()
                for user_id in all_user_ids:
                    print(f"Detecting conflicts for user {user_id} after sync...")
                    user_conflicts = conflict_service.detect_conflicts(user_id)
                    conflicts_detected += len(user_conflicts)
                    print(f"Detected {len(user_conflicts)} conflicts for user {user_id}")
            except Exception as e:
                print(f"Error detecting conflicts after sync: {e}")
        
        return jsonify({
            'message': f'Microsoft Calendar sync completed for {accounts_synced} account(s)',
            'synced_count': total_synced,
            'accounts_synced': accounts_synced,
            'total_accounts': len(microsoft_connections),
            'sync_results': sync_results,
            'conflicts_detected': conflicts_detected
        })
        
    except Exception as e:
        print(f"Microsoft sync error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@calendar_bp.route('/sync/all', methods=['POST'])
def sync_all_events():
    """Sync events from all connected calendars for all users (supports multiple Google accounts)"""
    from flask import current_app
    from flask_login import current_user
    from models.calendar_connection_model import CalendarConnection
    from models.user_model import User
    
    microsoft_enabled = current_app.config.get('MICROSOFT_ENABLED', False)
    try:
        print("Starting sync all for all connected accounts")
        
        # Get all active calendar connections
        google_connections = CalendarConnection.query.filter_by(
            provider='google',
            is_active=True,
            is_connected=True
        ).all()
        
        # Always get Microsoft connections (don't check flag)
        microsoft_connections = CalendarConnection.query.filter_by(
            provider='microsoft',
            is_active=True,
            is_connected=True
        ).all()
        
        # Fallback to legacy User model if no connections found
        use_legacy = len(google_connections) == 0 and len(microsoft_connections) == 0
        
        if use_legacy:
            # Legacy sync using User model
            if microsoft_enabled:
                all_users = User.query.filter(
                    (User.google_calendar_connected == True) | 
                    (User.microsoft_calendar_connected == True)
                ).all()
            else:
                all_users = User.query.filter(
                    User.google_calendar_connected == True
                ).all()
            
            if not all_users:
                return jsonify({
                    'message': 'No users with connected calendars found',
                    'total_synced': 0,
                    'sync_results': {'google': 0, 'microsoft': 0},
                    'conflicts_detected': 0
                })
            
            total_synced = 0
            google_synced = 0
            microsoft_synced = 0
            google_service = GoogleCalendarService()
            microsoft_service = MicrosoftCalendarService()
            
            for user in all_users:
                print(f"Syncing calendars for user: {user.email} (legacy)")
                
                if user.google_calendar_connected:
                    try:
                        synced_count = google_service.sync_events(user, days_back=30, days_forward=30)
                        google_synced += synced_count
                        total_synced += synced_count
                    except Exception as e:
                        print(f"Error syncing Google calendar for {user.email}: {e}")
                
                if microsoft_enabled and user.microsoft_calendar_connected:
                    try:
                        synced_count = microsoft_service.sync_events(user, days_back=30, days_forward=30)
                        microsoft_synced += synced_count
                        total_synced += synced_count
                    except Exception as e:
                        print(f"Error syncing Microsoft calendar for {user.email}: {e}")
            
            return jsonify({
                'message': f'Successfully synced {total_synced} total events from all calendars (legacy)',
                'total_synced': total_synced,
                'sync_results': {
                    'google': google_synced,
                    'microsoft': microsoft_synced
                },
                'users_synced': len(all_users),
                'conflicts_detected': 0
            })
        
        # New multi-account sync
        total_synced = 0
        google_synced = 0
        microsoft_synced = 0
        google_service = GoogleCalendarService()
        microsoft_service = MicrosoftCalendarService()
        sync_results = []
        all_user_ids = set()  # Track all user IDs for conflict detection
        
        # Sync all Google accounts
        for connection in google_connections:
            try:
                print(f"Syncing Google calendar for account: {connection.provider_account_email}")
                synced_count = google_service.sync_events_for_connection(connection, days_back=30, days_forward=30)
                google_synced += synced_count
                total_synced += synced_count
                all_user_ids.add(connection.user_id)  # Add user ID for conflict detection
                sync_results.append({
                    'provider': 'google',
                    'account_email': connection.provider_account_email,
                    'synced_count': synced_count
                })
            except Exception as e:
                print(f"Error syncing Google calendar for {connection.provider_account_email}: {e}")
                sync_results.append({
                    'provider': 'google',
                    'account_email': connection.provider_account_email,
                    'error': str(e)
                })
        
        # Sync all Microsoft accounts
        for connection in microsoft_connections:
            try:
                print(f"Syncing Microsoft calendar for account: {connection.provider_account_email}")
                # Use connection-based sync (same as Google) - this uses the token from CalendarConnection
                synced_count = microsoft_service.sync_events_for_connection(connection, days_back=30, days_forward=30)
                microsoft_synced += synced_count
                total_synced += synced_count
                all_user_ids.add(connection.user_id)  # Add user ID for conflict detection
                sync_results.append({
                    'provider': 'microsoft',
                    'account_email': connection.provider_account_email,
                    'synced_count': synced_count
                })
                print(f"Synced {synced_count} events for Microsoft account: {connection.provider_account_email}")
            except Exception as e:
                print(f"Error syncing Microsoft calendar for {connection.provider_account_email}: {e}")
                import traceback
                traceback.print_exc()
                sync_results.append({
                    'provider': 'microsoft',
                    'account_email': connection.provider_account_email,
                    'error': str(e)
                })
        
        # Automatically detect conflicts after sync for all users
        conflicts_detected = 0
        if all_user_ids:
            try:
                from services.conflict_service import ConflictDetectionService
                conflict_service = ConflictDetectionService()
                for user_id in all_user_ids:
                    print(f"Detecting conflicts for user {user_id} after sync...")
                    user_conflicts = conflict_service.detect_conflicts(user_id)
                    conflicts_detected += len(user_conflicts)
                    print(f"Detected {len(user_conflicts)} conflicts for user {user_id}")
            except Exception as e:
                print(f"Error detecting conflicts after sync: {e}")
        
        print(f"Sync all completed: {total_synced} total events from {len(google_connections)} Google account(s), {conflicts_detected} conflicts detected")
        
        return jsonify({
            'message': f'Successfully synced {total_synced} total events from all calendars',
            'total_synced': total_synced,
            'sync_results': {
                'google': google_synced,
                'microsoft': microsoft_synced,
                'google_accounts': len(google_connections),
                'microsoft_accounts': len(microsoft_connections)
            },
            'accounts_synced': len(google_connections) + len(microsoft_connections),
            'detailed_results': sync_results,
            'conflicts_detected': conflicts_detected
        })
        
    except Exception as e:
        print(f"Sync all error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@calendar_bp.route('/sync/bidirectional', methods=['POST'])
def sync_bidirectional():
    """Sync events bidirectionally between:
    - Google and Microsoft calendars (if Microsoft is enabled)
    - Multiple Google accounts (Google ↔ Google)
    """
    from flask import current_app
    from models.calendar_connection_model import CalendarConnection
    
    # Check if we have at least 2 Google accounts or Microsoft enabled
    google_connections = CalendarConnection.query.filter_by(
        provider='google',
        is_active=True,
        is_connected=True
    ).all()
    
    microsoft_enabled = current_app.config.get('MICROSOFT_ENABLED', False)
    
    if len(google_connections) < 2 and not microsoft_enabled:
        return jsonify({
            'error': 'Bidirectional sync requires at least 2 Google accounts OR Microsoft to be enabled',
            'message': 'Please connect at least 2 Google accounts, or enable Microsoft Calendar integration.'
        }), 400
    
    try:
        print("Starting bidirectional sync...")
        
        # Bidirectional sync NEVER sends notifications (this is just mirroring existing events)
        print(f"Bidirectional sync: NEVER sending notifications (this is just mirroring existing events)")
        
        bidirectional_service = BidirectionalSyncService()
        result = bidirectional_service.sync_bidirectional(
            days_back=30, 
            days_forward=30,
            send_notifications=False  # Always false for bidirectional sync
        )
        
        return jsonify({
            'message': 'Bidirectional sync completed successfully (NO notifications sent - this is just mirroring existing events)',
            'google_to_microsoft': result.get('google_to_microsoft', 0),
            'microsoft_to_google': result.get('microsoft_to_google', 0),
            'google_to_google': result.get('google_to_google', 0),
            'users_processed': result.get('users_processed', 0),
            'total_synced': result.get('google_to_microsoft', 0) + result.get('microsoft_to_google', 0) + result.get('google_to_google', 0),
            'notifications_enabled': False
        })
        
    except Exception as e:
        print(f"Bidirectional sync error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@calendar_bp.route('/sync/view-only', methods=['POST'])
def sync_view_only():
    """Sync events for view-only purposes (no creation in external calendars)"""
    try:
        print("Starting view-only sync...")
        
        # Get all users with connected calendars (only Google if Microsoft is disabled)
        from flask import current_app
        from models.user_model import User
        microsoft_enabled = current_app.config.get('MICROSOFT_ENABLED', False)
        if microsoft_enabled:
            all_users = User.query.filter(
                (User.google_calendar_connected == True) | 
                (User.microsoft_calendar_connected == True)
            ).all()
        else:
            all_users = User.query.filter(
                User.google_calendar_connected == True
            ).all()
        
        if not all_users:
            return jsonify({
                'message': 'No users with connected calendars found',
                'total_synced': 0,
                'sync_results': {'google': 0, 'microsoft': 0}
            })
        
        total_synced = 0
        google_synced = 0
        microsoft_synced = 0
        
        google_service = GoogleCalendarService()
        microsoft_service = MicrosoftCalendarService()
        
        for user in all_users:
            print(f"View-only syncing calendars for user: {user.email}")
            
            # Sync Google calendar if connected (read-only)
            if user.google_calendar_connected:
                try:
                    synced_count = google_service.sync_events(user, days_back=30, days_forward=30)
                    google_synced += synced_count
                    total_synced += synced_count
                    print(f"View-only synced {synced_count} Google events for {user.email}")
                except Exception as e:
                    print(f"Error view-only syncing Google calendar for {user.email}: {e}")
            
            # Sync Microsoft calendar if connected and enabled (read-only)
            if microsoft_enabled and user.microsoft_calendar_connected:
                try:
                    synced_count = microsoft_service.sync_events(user, days_back=30, days_forward=30)
                    microsoft_synced += synced_count
                    total_synced += synced_count
                    print(f"View-only synced {synced_count} Microsoft events for {user.email}")
                except Exception as e:
                    print(f"Error view-only syncing Microsoft calendar for {user.email}: {e}")
        
        print(f"View-only sync completed: {total_synced} total events fetched for display")
        
        return jsonify({
            'message': f'Successfully fetched {total_synced} events for unified view (no external calendar creation)',
            'total_synced': total_synced,
            'sync_results': {
                'google': google_synced,
                'microsoft': microsoft_synced
            },
            'users_synced': len(all_users),
            'sync_type': 'view_only'
        })
        
    except Exception as e:
        print(f"View-only sync error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@calendar_bp.route('/conflicts', methods=['GET'])
def get_conflicts():
    """Get calendar conflicts for the current user"""
    try:
        # Try to get logged-in user first
        from flask_login import current_user
        if current_user.is_authenticated:
            user = current_user
        else:
            # Fallback to test user for development
            user = get_test_user()
        
        print(f"Detecting conflicts for user: {user.id} ({user.email})")
        
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        try:
            conflict_service = ConflictDetectionService()
            
            if start_date:
                start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00')).date()
            if end_date:
                end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00')).date()
            
            conflicts = conflict_service.detect_conflicts(
                user.id, 
                start_date=start_date, 
                end_date=end_date
            )
            print(f"Found {len(conflicts)} conflicts for user {user.id}")
        except Exception as e:
            print(f"Conflict detection error: {str(e)}")
            import traceback
            traceback.print_exc()
            conflicts = []
        
        return jsonify({
            'conflicts': conflicts,
            'count': len(conflicts),
            'user_id': user.id,
            'user_email': user.email
        })
        
    except Exception as e:
        print(f"Error getting conflicts: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@calendar_bp.route('/free-slots', methods=['GET'])
def get_free_slots():
    """Get free time slots for scheduling"""
    try:
        # Try to get logged-in user first
        from flask_login import current_user
        if current_user.is_authenticated:
            user = current_user
        else:
            # Fallback to test user for development
            user = get_test_user()
        
        print(f"Finding free slots for user: {user.id} ({user.email})")
        
        # Get query parameters
        date_str = request.args.get('date')
        duration = int(request.args.get('duration', 60))  # minutes
        start_hour = int(request.args.get('start_hour', 0))  # Default to 0 (entire day)
        end_hour = int(request.args.get('end_hour', 24))    # Default to 24 (entire day)
        
        if not date_str:
            return jsonify({'error': 'Date parameter is required'}), 400
        
        try:
            date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
        except:
            # Try parsing as date string directly
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        try:
            conflict_service = ConflictDetectionService()
            free_slots = conflict_service.find_free_slots(
                user.id,
                date,
                duration_minutes=duration,
                start_hour=start_hour,
                end_hour=end_hour
            )
            print(f"Found {len(free_slots)} free slots for user {user.id}")
        except Exception as e:
            print(f"Free slots detection error: {str(e)}")
            import traceback
            traceback.print_exc()
            free_slots = []
        
        return jsonify({
            'date': date.isoformat(),
            'duration_minutes': duration,
            'free_slots': free_slots,
            'count': len(free_slots),
            'user_id': user.id
        })
        
    except Exception as e:
        print(f"Error getting free slots: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@calendar_bp.route('/suggest-meeting', methods=['POST'])
def suggest_meeting_time():
    """Suggest meeting times based on availability"""
    try:
        user = get_test_user()
        
        data = request.get_json() or {}
        duration = data.get('duration_minutes', 60)
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        preferred_days = data.get('preferred_days', [0, 1, 2, 3, 4])  # Mon-Fri
        preferred_hours = data.get('preferred_hours', {'start': 9, 'end': 17})
        
        if start_date:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00')).date()
        if end_date:
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00')).date()
        
        try:
            conflict_service = ConflictDetectionService()
            suggestions = conflict_service.suggest_meeting_time(
                user.id,
                duration_minutes=duration,
                start_date=start_date,
                end_date=end_date,
                preferred_days=preferred_days,
                preferred_hours=preferred_hours
            )
        except Exception as e:
            print(f"Meeting suggestion error: {str(e)}")
            suggestions = []
        
        return jsonify({
            'suggestions': suggestions,
            'count': len(suggestions)
        })
        
    except Exception as e:
        print(f"Error suggesting meeting times: {str(e)}")
        return jsonify({'error': str(e)}), 500

@calendar_bp.route('/summary', methods=['GET'])
def get_calendar_summary():
    """Get calendar summary and statistics"""
    try:
        # Try to get logged-in user first
        from flask_login import current_user
        if current_user.is_authenticated:
            user = current_user
        else:
            # Fallback to test user for development
            user = get_test_user()
        
        print(f"Generating summary for user: {user.id} ({user.email})")
        
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date:
            start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00')).date()
        if end_date:
            end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00')).date()
        
        try:
            conflict_service = ConflictDetectionService()
            summary = conflict_service.get_calendar_summary(
                user.id,
                start_date=start_date,
                end_date=end_date
            )
            print(f"Summary generated successfully: {summary.get('total_events', 0)} events")
        except Exception as e:
            print(f"Summary generation error: {str(e)}")
            import traceback
            traceback.print_exc()
            # Return basic summary if service fails
            events = Event.query.filter_by(user_id=user.id).all()
            summary = {
                'total_events': len(events),
                'google_events': len([e for e in events if e.provider == 'google']),
                'microsoft_events': len([e for e in events if e.provider == 'microsoft']),
                'conflicts': 0
            }
        
        return jsonify(summary)
        
    except Exception as e:
        print(f"Error getting summary: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@calendar_bp.route('/test', methods=['GET'])
def test_endpoint():
    """Simple test endpoint to verify the backend is working"""
    try:
        user = get_test_user()
        event_count = Event.query.filter_by(user_id=user.id).count()
        
        return jsonify({
            'message': 'Calendar backend is working!',
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user.id,
            'user_email': user.email,
            'events_count': event_count
        })
    except Exception as e:
        return jsonify({
            'message': 'Calendar backend has issues',
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@calendar_bp.route('/create-sample-events', methods=['POST'])
def create_sample_events_endpoint():
    """Create sample events for testing (temporary endpoint)"""
    try:
        user = get_test_user()
        
        # Create sample events
        events = create_sample_events(user)
        
        return jsonify({
            'message': f'Created {len(events)} sample events',
            'events_count': len(events),
            'user_id': user.id
        })
        
    except Exception as e:
        print(f"Error creating sample events: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@calendar_bp.route('/clear-events', methods=['DELETE'])
def clear_events():
    """Clear all events for testing purposes"""
    try:
        user = get_test_user()
        
        # Clear all events for the user
        Event.query.filter_by(user_id=user.id).delete()
        db.session.commit()
        
        return jsonify({
            'message': 'All events cleared successfully',
            'cleared_count': 0
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error clearing events: {e}")
        return jsonify({'error': str(e)}), 500

@calendar_bp.route('/clear-conflicts', methods=['POST'])
def clear_conflicts():
    """Clear all conflict flags and re-run conflict detection"""
    try:
        user = get_test_user()
        
        # Clear all conflict flags
        events = Event.query.filter_by(user_id=user.id).all()
        for event in events:
            event.has_conflict = False
            event.conflict_with = None
        
        db.session.commit()
        
        # Re-run conflict detection
        conflict_service = ConflictDetectionService()
        conflicts = conflict_service.detect_conflicts(user.id)
        
        return jsonify({
            'message': 'Conflicts cleared and re-detected',
            'conflicts_found': len(conflicts),
            'total_events': len(events)
        })
        
    except Exception as e:
        db.session.rollback()
        print(f"Error clearing conflicts: {e}")
        return jsonify({'error': str(e)}), 500

@calendar_bp.route('/check-duplicates', methods=['GET'])
def check_duplicates():
    """Check for duplicate events and provide detailed information"""
    try:
        user = get_test_user()
        
        # Get all events for the user
        events = Event.query.filter_by(user_id=user.id).order_by(Event.start_time).all()
        
        # Group events by their unique key
        event_groups = {}
        for event in events:
            normalized_title = event.title.lower().strip()
            start_time_str = event.start_time.strftime('%Y-%m-%d %H:%M')
            end_time_str = event.end_time.strftime('%Y-%m-%d %H:%M')
            
            event_key = (normalized_title, start_time_str, end_time_str)
            
            if event_key not in event_groups:
                event_groups[event_key] = []
            event_groups[event_key].append(event)
        
        # Find duplicates
        duplicates = []
        for event_key, event_list in event_groups.items():
            if len(event_list) > 1:
                duplicates.append({
                    'title': event_list[0].title,
                    'start_time': event_list[0].start_time.isoformat(),
                    'end_time': event_list[0].end_time.isoformat(),
                    'events': [
                        {
                            'id': event.id,
                            'provider': event.provider,
                            'created_at': event.created_at.isoformat(),
                            'title': event.title
                        }
                        for event in event_list
                    ]
                })
        
        return jsonify({
            'total_events': len(events),
            'unique_events': len(event_groups),
            'duplicates_found': len(duplicates),
            'duplicates': duplicates
        })
        
    except Exception as e:
        print(f"Error checking duplicates: {e}")
        return jsonify({'error': str(e)}), 500

@calendar_bp.route('/create-event', methods=['POST'])
def create_new_event():
    """Create a NEW event and send notifications to participants"""
    from flask import current_app
    microsoft_enabled = current_app.config.get('MICROSOFT_ENABLED', False)
    
    try:
        print("Creating NEW event with notifications...")
        
        data = request.get_json() or {}
        
        # Validate required fields
        required_fields = ['title', 'start_time', 'end_time']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Parse datetime strings
        try:
            start_time = datetime.fromisoformat(data['start_time'].replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(data['end_time'].replace('Z', '+00:00'))
        except ValueError as e:
            return jsonify({'error': f'Invalid datetime format: {e}'}), 400
        
        # Prepare event data
        event_data = {
            'title': data['title'],
            'description': data.get('description', ''),
            'location': data.get('location', ''),
            'start_time': start_time,
            'end_time': end_time,
            'all_day': data.get('all_day', False),
            'attendees': data.get('attendees', [])
        }
        
        target_calendar = data.get('target_calendar', 'google')  # Default to 'google' if Microsoft disabled
        
        # If Microsoft is disabled and user requests 'both' or 'microsoft', default to 'google'
        if not microsoft_enabled:
            if target_calendar in ['microsoft', 'both']:
                target_calendar = 'google'
                print("Microsoft is disabled. Creating event in Google Calendar only.")
        
        # Create the event
        event_creation_service = EventCreationService()
        result = event_creation_service.create_new_event(event_data, target_calendar)
        
        return jsonify({
            'message': result['message'],
            'google_created': result['google_created'],
            'microsoft_created': result['microsoft_created'],
            'event_title': event_data['title'],
            'microsoft_enabled': microsoft_enabled
        })
        
    except Exception as e:
        print(f"Event creation error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500