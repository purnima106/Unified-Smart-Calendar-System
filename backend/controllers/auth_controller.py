from flask import Blueprint, request, jsonify, session, redirect
from flask_login import login_user, logout_user, login_required, current_user
from models.user_model import User, db
from models.calendar_connection_model import CalendarConnection
from models.event_model import Event
from models.event_mirror_mapping_model import EventMirrorMapping
from services.google_service import GoogleCalendarService
from services.microsoft_service import MicrosoftCalendarService
import json
import base64


def decode_oauth_state(state_str):
    """Decode base64-encoded JSON state payload."""
    if not state_str:
        return {}
    try:
        padding = '=' * (-len(state_str) % 4)
        decoded_bytes = base64.urlsafe_b64decode(state_str + padding)
        data = json.loads(decoded_bytes.decode('utf-8'))
        if isinstance(data, dict):
            return data
    except Exception as e:
        print(f"State decode failed: {e}")
    return {}


def _reassign_connection_data(provider: str, old_user_id: int, new_user_id: int, account_email: str):
    """
    Ensure all events and mirror mappings that belong to a calendar connection
    follow the connection when it is reassigned to a different user.
    """
    if old_user_id is None or new_user_id is None or old_user_id == new_user_id:
        return

    provider = provider.lower()
    email_prefix = f"{account_email}:"

    # Update events stored for this connection (provider_event_id uses "email:event_id" format)
    events_to_update = Event.query.filter(
        Event.user_id == old_user_id,
        Event.provider == provider,
        Event.provider_event_id.like(f"{email_prefix}%")
    ).all()
    for event in events_to_update:
        event.user_id = new_user_id

    # Update mirror mappings referencing this connection
    mappings_to_update = EventMirrorMapping.query.filter_by(user_id=old_user_id).all()
    for mapping in mappings_to_update:
        mapping.user_id = new_user_id

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/check-auth')
def check_auth():
    """Check if user is authenticated without requiring login"""
    if current_user.is_authenticated:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': current_user.id,
                'email': current_user.email,
                'name': current_user.name,
                'google_connected': current_user.google_calendar_connected,
                'microsoft_connected': current_user.microsoft_calendar_connected,
                'has_connected_calendars': current_user.has_connected_calendars()
            }
        })
    else:
        return jsonify({'authenticated': False}), 401

@auth_bp.route('/login/google')
def google_login():
    """Initiate Google OAuth login"""
    try:
        # Store current user ID in session if logged in (for adding account to existing user)
        if current_user.is_authenticated:
            session['adding_account_user_id'] = current_user.id
            session['adding_account_provider'] = 'google'
            print(f"Storing user {current_user.id} in session for Google account addition")
        
        google_service = GoogleCalendarService()
        target_user_id = current_user.id if current_user.is_authenticated else None
        auth_url = google_service.get_auth_url(target_user_id=target_user_id)
        
        # Debug: Print session info
        print(f"Session ID: {session.sid if hasattr(session, 'sid') else 'No session ID'}")
        print(f"Stored state after auth URL generation: {session.get('google_oauth_state')}")
        
        return jsonify({'auth_url': auth_url})
    except Exception as e:
        print(f"Google login error: {str(e)}")
        return jsonify({'error': f'Google OAuth configuration error: {str(e)}'}), 500

@auth_bp.route('/google/callback')
def google_callback():
    """Handle Google OAuth callback - supports multi-account via CalendarConnection"""
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        
        if not code:
            return jsonify({'error': 'No authorization code received'}), 400
        
        if not state:
            return jsonify({'error': 'No state parameter received'}), 400
        
        # Debug: Print state information
        print(f"Received state: {state}")
        print(f"Stored state: {session.get('google_oauth_state')}")
        
        google_service = GoogleCalendarService()
        token_info = google_service.handle_callback(code, state)
        
        # Get user info from Google
        user_info = google_service.get_user_info(token_info['token'])
        google_account_email = user_info.get('email', 'user@example.com')
        google_account_name = user_info.get('name', 'Google User')
        
        print(f"Google account email: {google_account_email}")
        print(f"Google account name: {google_account_name}")
        
        # Decode state payload for additional metadata
        state_payload = decode_oauth_state(state)
        state_user_id = state_payload.get('target_user_id')
        state_provider = state_payload.get('provider')
        
        # Check if we stored a user ID in session (from "Add Account" button click)
        stored_user_id = session.get('adding_account_user_id') or state_user_id
        stored_provider = session.get('adding_account_provider') or state_provider
        if stored_user_id is not None:
            try:
                stored_user_id = int(stored_user_id)
            except (TypeError, ValueError):
                print(f"Invalid stored_user_id value: {stored_user_id}")
                stored_user_id = None
        
        # Clear the stored values
        session.pop('adding_account_user_id', None)
        session.pop('adding_account_provider', None)
        
        # Determine which user should own this Google connection
        existing_connection_any_user = CalendarConnection.query.filter_by(
            provider='google',
            provider_account_email=google_account_email
        ).first()
        
        target_user = None
        if stored_user_id and stored_provider == 'google':
            target_user = User.query.get(stored_user_id)
            if target_user:
                print(f"Using stored user from state/session: {target_user.email} (ID: {target_user.id})")
            else:
                print(f"Stored user ID {stored_user_id} not found")
        if not target_user and current_user.is_authenticated:
            target_user = current_user
            print(f"Using currently logged in user: {target_user.email} (ID: {target_user.id})")
        if not target_user and existing_connection_any_user:
            target_user = existing_connection_any_user.user
            print(f"Using user from existing connection: {target_user.email} (ID: {target_user.id})")
        if not target_user:
            target_user = User.query.filter_by(email=google_account_email).first()
            if target_user:
                print(f"Using user found by email: {target_user.email} (ID: {target_user.id})")
        if not target_user:
            target_user = User(email=google_account_email, name=google_account_name)
            db.session.add(target_user)
            db.session.flush()
            print(f"Created new user for Google account: {target_user.email} (ID: {target_user.id})")
        
        # Ensure connection exists and belongs to target_user
        if existing_connection_any_user:
            connection = existing_connection_any_user
            if connection.user_id != target_user.id:
                print(f"Reassigning Google connection {google_account_email} from user {connection.user_id} to {target_user.id}")
                old_user_id = connection.user_id
                connection.user_id = target_user.id
                _reassign_connection_data('google', old_user_id, target_user.id, google_account_email)
        else:
            connection = CalendarConnection(
                user_id=target_user.id,
                provider='google',
                provider_account_email=google_account_email,
                provider_account_name=google_account_name,
                calendar_id='primary'
            )
            db.session.add(connection)
            print(f"Created new CalendarConnection for {google_account_email}")
        
        connection.set_token(token_info)
        connection.is_connected = True
        connection.is_active = True
        connection.provider_account_name = google_account_name
        
        # Keep legacy token info updated
        target_user.set_google_token(token_info)
        
        db.session.commit()
        
        # Log in/keep logged in the target user
        login_user(target_user, remember=True)
        user = target_user
        
        # Auto-sync Google Calendar events for this connection
        try:
            connection = CalendarConnection.query.filter_by(
                user_id=user.id,
                provider='google',
                provider_account_email=google_account_email
            ).first()
            
            if connection:
                print(f"Auto-syncing events for connection: {google_account_email}")
                google_service.sync_events_for_connection(connection, days_back=30, days_forward=30)
            else:
                # Fallback to legacy sync
                print(f"Falling back to legacy sync for user: {user.email}")
                google_service.sync_events(user, days_back=30, days_forward=30)
        except Exception as sync_error:
            print(f"Auto-sync failed: {sync_error}")
            import traceback
            traceback.print_exc()
            # Don't fail the login if sync fails
        
        # Redirect to frontend
        return redirect('http://localhost:5173/')
        
    except Exception as e:
        print(f"Google callback error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/login/microsoft')
def microsoft_login():
    """Initiate Microsoft OAuth login"""
    try:
        # Store current user ID in session if logged in (for adding account to existing user)
        if current_user.is_authenticated:
            session['adding_account_user_id'] = current_user.id
            session['adding_account_provider'] = 'microsoft'
            print(f"Storing user {current_user.id} in session for Microsoft account addition")
        
        microsoft_service = MicrosoftCalendarService()
        target_user_id = current_user.id if current_user.is_authenticated else None
        auth_url = microsoft_service.get_auth_url(target_user_id=target_user_id)
        return jsonify({'auth_url': auth_url})
    except Exception as e:
        print(f"Microsoft login error: {str(e)}")
        return jsonify({'error': f'Microsoft OAuth configuration error: {str(e)}'}), 500

@auth_bp.route('/microsoft/callback')
def microsoft_callback():
    """Handle Microsoft OAuth callback - supports multi-account via CalendarConnection"""
    try:
        code = request.args.get('code')
        state = request.args.get('state')
        
        if not code:
            return jsonify({'error': 'No authorization code received'}), 400
        
        if not state:
            return jsonify({'error': 'No state parameter received'}), 400
        
        microsoft_service = MicrosoftCalendarService()
        
        # Try to exchange code for tokens
        try:
            token_info = microsoft_service.handle_callback(code, state)
        except Exception as token_error:
            error_msg = str(token_error)
            print(f"Token exchange error: {error_msg}")
            
            # If code was already redeemed, it means the connection might have been created
            # but the redirect failed. We'll redirect to frontend with a helpful message.
            if "already redeemed" in error_msg.lower() or "AADSTS54005" in error_msg:
                print("Authorization code already redeemed. This usually means:")
                print("  1. The connection was already created successfully")
                print("  2. Or the code was used in a previous attempt")
                print("Redirecting to frontend - user should check their connections or try again")
                
                # Redirect to frontend - user can check if connection exists or try again
                return redirect('http://localhost:5173/?microsoft_auth=retry&message=Authorization code was already used. Please check if your Microsoft account is already connected, or try connecting again.')
            else:
                # Re-raise other errors
                raise
        
        # Get user info from Microsoft
        user_info = microsoft_service.get_user_info(token_info['access_token'])
        microsoft_account_email = user_info.get('email', 'user@example.com')
        microsoft_account_name = user_info.get('name', 'Microsoft User')
        
        print(f"Microsoft account email: {microsoft_account_email}")
        print(f"Microsoft account name: {microsoft_account_name}")
        
        # Decode state payload metadata
        state_payload = decode_oauth_state(state)
        state_user_id = state_payload.get('target_user_id')
        state_provider = state_payload.get('provider')
        
        # Check if we stored a user ID in session (from "Add Account" button click")
        stored_user_id = session.get('adding_account_user_id') or state_user_id
        stored_provider = session.get('adding_account_provider') or state_provider
        if stored_user_id is not None:
            try:
                stored_user_id = int(stored_user_id)
            except (TypeError, ValueError):
                print(f"Invalid stored_user_id value: {stored_user_id}")
                stored_user_id = None
        
        # Clear the stored values
        session.pop('adding_account_user_id', None)
        session.pop('adding_account_provider', None)
        
        existing_connection_any_user = CalendarConnection.query.filter_by(
            provider='microsoft',
            provider_account_email=microsoft_account_email
        ).first()
        
        target_user = None
        if stored_user_id and stored_provider == 'microsoft':
            target_user = User.query.get(stored_user_id)
            if target_user:
                print(f"Using stored user from state/session: {target_user.email} (ID: {target_user.id})")
            else:
                print(f"Stored user ID {stored_user_id} not found")
        if not target_user and current_user.is_authenticated:
            target_user = current_user
            print(f"Using currently logged in user: {target_user.email} (ID: {target_user.id})")
        if not target_user and existing_connection_any_user:
            target_user = existing_connection_any_user.user
            print(f"Using user from existing connection: {target_user.email} (ID: {target_user.id})")
        if not target_user:
            target_user = User.query.filter_by(email=microsoft_account_email).first()
            if target_user:
                print(f"Using user found by email: {target_user.email} (ID: {target_user.id})")
        if not target_user:
            target_user = User(email=microsoft_account_email, name=microsoft_account_name)
            db.session.add(target_user)
            db.session.flush()  # Flush to get user.id before creating connection
            print(f"Created new user: {microsoft_account_email} (ID: {target_user.id})")
        
        if existing_connection_any_user:
            connection = existing_connection_any_user
            if connection.user_id != target_user.id:
                print(f"Reassigning Microsoft connection {microsoft_account_email} from user {connection.user_id} to {target_user.id}")
                old_user_id = connection.user_id
                connection.user_id = target_user.id
                _reassign_connection_data('microsoft', old_user_id, target_user.id, microsoft_account_email)
        else:
            connection = CalendarConnection(
                user_id=target_user.id,
                provider='microsoft',
                provider_account_email=microsoft_account_email,
                provider_account_name=microsoft_account_name,
                calendar_id='default'
            )
            db.session.add(connection)
            print(f"Created CalendarConnection for {microsoft_account_email}")
        
        connection.set_token(token_info)
        connection.is_connected = True
        connection.is_active = True
        connection.provider_account_name = microsoft_account_name
        
        # Also set legacy User model fields for backward compatibility
        target_user.set_microsoft_token(token_info)
        
        db.session.commit()
        
        # Log in user
        login_user(target_user, remember=True)
        user = target_user
        
        # Auto-sync Microsoft Calendar events for this connection
        try:
            connection = CalendarConnection.query.filter_by(
                user_id=user.id,
                provider='microsoft',
                provider_account_email=microsoft_account_email
            ).first()
            
            if connection:
                print(f"Auto-syncing events for connection: {microsoft_account_email}")
                # Note: Microsoft service doesn't have sync_events_for_connection yet
                # Fallback to legacy sync for now
                microsoft_service.sync_events(user, days_back=30, days_forward=30)
            else:
                # Fallback to legacy sync
                print(f"Falling back to legacy sync for user: {user.email}")
                microsoft_service.sync_events(user, days_back=30, days_forward=30)
        except Exception as sync_error:
            print(f"Auto-sync failed: {sync_error}")
            import traceback
            traceback.print_exc()
            # Don't fail the login if sync fails
        
        # Redirect to frontend
        return redirect('http://localhost:5173/')
        
    except Exception as e:
        print(f"Microsoft callback error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    return jsonify({'message': 'Logged out successfully'})

@auth_bp.route('/user/profile')
@login_required
def get_user_profile():
    """Get current user profile"""
    return jsonify({
        'id': current_user.id,
        'email': current_user.email,
        'name': current_user.name,
        'google_connected': current_user.google_calendar_connected,
        'microsoft_connected': current_user.microsoft_calendar_connected,
        'has_connected_calendars': current_user.has_connected_calendars()
    })

@auth_bp.route('/user/connections')
@login_required
def get_user_connections():
    """Get user's calendar connections status (legacy format)"""
    return jsonify({
        'google': {
            'connected': current_user.google_calendar_connected,
            'last_sync': None  # You could add last sync timestamp to User model
        },
        'microsoft': {
            'connected': current_user.microsoft_calendar_connected,
            'last_sync': None
        }
    })

@auth_bp.route('/user/connections/list')
@login_required
def list_all_connections():
    """Get all calendar connections for the current user (multi-account support)"""
    try:
        # Get all connections for current user
        connections = CalendarConnection.query.filter_by(
            user_id=current_user.id
        ).order_by(CalendarConnection.created_at.desc()).all()
        
        # Convert to dictionary format
        connections_list = [conn.to_dict() for conn in connections]
        
        print(f"Found {len(connections_list)} connections for user {current_user.email}")
        
        return jsonify({
            'connections': connections_list,
            'count': len(connections_list)
        })
    except Exception as e:
        print(f"Error listing connections: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'connections': []}), 500

@auth_bp.route('/user/connections/<int:connection_id>', methods=['DELETE'])
@login_required
def remove_connection(connection_id):
    """Remove a calendar connection"""
    try:
        connection = CalendarConnection.query.filter_by(
            id=connection_id,
            user_id=current_user.id
        ).first()
        
        if not connection:
            return jsonify({'error': 'Connection not found'}), 404
        
        # Mark as inactive instead of deleting (soft delete)
        connection.is_active = False
        connection.is_connected = False
        db.session.commit()
        
        print(f"Removed connection {connection_id} for user {current_user.email}")
        
        return jsonify({
            'message': 'Connection removed successfully',
            'connection_id': connection_id
        })
    except Exception as e:
        print(f"Error removing connection: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/user/connections/<int:connection_id>/toggle', methods=['POST'])
@login_required
def toggle_connection(connection_id):
    """Toggle a connection's active status"""
    try:
        connection = CalendarConnection.query.filter_by(
            id=connection_id,
            user_id=current_user.id
        ).first()
        
        if not connection:
            return jsonify({'error': 'Connection not found'}), 404
        
        connection.is_active = not connection.is_active
        db.session.commit()
        
        print(f"Toggled connection {connection_id} to {'active' if connection.is_active else 'inactive'}")
        
        return jsonify({
            'message': f"Connection {'activated' if connection.is_active else 'deactivated'}",
            'connection': connection.to_dict()
        })
    except Exception as e:
        print(f"Error toggling connection: {str(e)}")
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@auth_bp.route('/test-oauth')
def test_oauth():
    """Test OAuth configuration"""
    try:
        # Test Google OAuth
        google_service = GoogleCalendarService()
        google_auth_url = google_service.get_auth_url()
        
        # Test Microsoft OAuth
        microsoft_service = MicrosoftCalendarService()
        microsoft_auth_url = microsoft_service.get_auth_url()
        
        return jsonify({
            'status': 'success',
            'message': 'OAuth configuration is working',
            'google_auth_url': google_auth_url,
            'microsoft_auth_url': microsoft_auth_url,
            'google_configured': bool(google_service.client_id),
            'microsoft_configured': bool(microsoft_service.client_id)
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'OAuth configuration error: {str(e)}',
            'google_configured': False,
            'microsoft_configured': False
        }), 500
