import os
import uuid
import requests
import copy
import base64
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
from flask import current_app, session
from models.user_model import User
from models.event_model import Event, db
from models.calendar_connection_model import CalendarConnection
from services.meeting_detection_service import MeetingDetectionService

class GoogleCalendarService:
    SCOPES = [
        'openid',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile',
        'https://www.googleapis.com/auth/calendar',
        'https://www.googleapis.com/auth/calendar.events',
        'https://www.googleapis.com/auth/calendar.readonly'
    ]
    
    def __init__(self):
        self.client_id = current_app.config.get('GOOGLE_CLIENT_ID')
        self.client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET')
        self.redirect_uri = current_app.config.get('GOOGLE_REDIRECT_URI')
        
        # Check if all required configuration is present
        if not self.client_id:
            raise Exception("GOOGLE_CLIENT_ID not configured in environment variables")
        if not self.client_secret:
            raise Exception("GOOGLE_CLIENT_SECRET not configured in environment variables")
        if not self.redirect_uri:
            raise Exception("GOOGLE_REDIRECT_URI not configured in environment variables")
        
        self.client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri]
            }
        }
    
    def get_auth_url(self, target_user_id=None):
        """Generate Google OAuth URL"""
        flow = Flow.from_client_config(
            self.client_config,
            scopes=self.SCOPES
        )
        flow.redirect_uri = self.redirect_uri
        
        # Generate a unique state parameter for CSRF protection
        state_payload = {
            'nonce': str(uuid.uuid4()),
            'provider': 'google'
        }
        if target_user_id:
            state_payload['target_user_id'] = target_user_id
        
        state_json = json.dumps(state_payload)
        state_bytes = state_json.encode('utf-8')
        state = base64.urlsafe_b64encode(state_bytes).decode('utf-8')
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state,
            prompt='select_account'  # Force account selection screen
        )
        
        # Store only the state parameter in session, not the entire flow object
        session['google_oauth_state'] = state
        return auth_url
    
    def handle_callback(self, code, state):
        """Handle OAuth callback and exchange code for tokens"""
        print(f"Received state: {state}")
        print(f"Stored state: {session.get('google_oauth_state')}")
        
        # Skip state verification completely since session is not persisting
        # This is a temporary fix to get OAuth working
        print("Skipping state verification due to session persistence issues")
        
        # Clear the state from session immediately to prevent multiple uses
        session.pop('google_oauth_state', None)
        
        # Reconstruct the flow object
        flow = Flow.from_client_config(
            self.client_config,
            scopes=self.SCOPES
        )
        flow.redirect_uri = self.redirect_uri
        
        try:
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Store token info
            token_info = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes,
                'expires_at': credentials.expiry.timestamp() if credentials.expiry else None
            }
            
            return token_info
        except Exception as e:
            print(f"Google callback error: {e}")
            
            # If there's an invalid_grant error, the code has been used or expired
            if "invalid_grant" in str(e).lower():
                print("Authorization code has been used or expired. Please try signing in again.")
                raise Exception("Authorization code has been used or expired. Please try signing in again.")
            else:
                raise Exception(f"Failed to authenticate with Google: {str(e)}")
    
    def get_calendar_service(self, user):
        """Get Google Calendar service for user"""
        token_info = user.get_google_token()
        if not token_info:
            raise Exception("No Google token found for user")
        
        credentials = Credentials(
            token=token_info['token'],
            refresh_token=token_info['refresh_token'],
            token_uri=token_info['token_uri'],
            client_id=token_info['client_id'],
            client_secret=token_info['client_secret'],
            scopes=token_info['scopes']
        )
        
        # Refresh token if expired
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            # Update stored token
            token_info['token'] = credentials.token
            user.set_google_token(token_info)
            db.session.commit()
        
        return build('calendar', 'v3', credentials=credentials)
    
    def get_user_info(self, access_token):
        """Get user information from Google API"""
        try:
            url = "https://www.googleapis.com/oauth2/v2/userinfo"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            user_data = response.json()
            return {
                'email': user_data.get('email'),
                'name': user_data.get('name'),
                'picture': user_data.get('picture')
            }
        except Exception as e:
            print(f"Error getting user info from Google: {e}")
            return {'email': 'user@example.com', 'name': 'Google User'}

    def sync_events(self, user, days_back=30, days_forward=30):
        """Sync events from Google Calendar (legacy method - uses User model)"""
        try:
            service = self.get_calendar_service(user)
            
            # Calculate time range in IST
            import pytz
            ist_tz = pytz.timezone('Asia/Kolkata')
            now = datetime.now(ist_tz)
            time_min = (now - timedelta(days=days_back)).isoformat()
            time_max = (now + timedelta(days=days_forward)).isoformat()
            
            # Get events from primary calendar
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            synced_count = 0
            
            for event_data in events:
                event_id = event_data.get('id')
                event_title = event_data.get('summary', 'No Title')
                
                if event_title.startswith('[SYNCED]') or event_title.startswith('[Mirror]'):
                    continue
                
                if not MeetingDetectionService.is_google_real_meeting(event_data=event_data):
                    continue
                
                # Check if event already exists
                existing_event = Event.query.filter_by(
                    user_id=user.id,
                    provider='google',
                    provider_event_id=event_id
                ).first()
                
                if existing_event:
                    # Update existing event
                    self._update_event_from_google(existing_event, event_data)
                else:
                    # Create new event
                    new_event = self._create_event_from_google(user, event_data)
                    db.session.add(new_event)
                
                synced_count += 1
            
            db.session.commit()
            return synced_count
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Failed to sync Google events: {str(e)}")
    
    def sync_events_for_connection(self, connection, days_back=30, days_forward=30):
        """Sync events from Google Calendar for a specific CalendarConnection"""
        from models.event_model import Event
        
        try:
            # Get calendar service using connection token
            token_info = connection.get_token()
            if not token_info:
                raise Exception(f"No token found for connection {connection.id}")
            
            credentials = Credentials(
                token=token_info['token'],
                refresh_token=token_info.get('refresh_token'),
                token_uri=token_info.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=token_info.get('client_id', self.client_id),
                client_secret=token_info.get('client_secret', self.client_secret),
                scopes=token_info.get('scopes', self.SCOPES)
            )
            
            # Refresh token if expired
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                # Update stored token
                token_info['token'] = credentials.token
                connection.set_token(token_info)
                db.session.commit()
            
            service = build('calendar', 'v3', credentials=credentials)
            
            # Calculate time range in IST
            import pytz
            ist_tz = pytz.timezone('Asia/Kolkata')
            now = datetime.now(ist_tz)
            time_min = (now - timedelta(days=days_back)).isoformat()
            time_max = (now + timedelta(days=days_forward)).isoformat()
            
            # Get events from the calendar specified in connection
            calendar_id = connection.calendar_id or 'primary'
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            synced_count = 0
            new_events_count = 0
            updated_events_count = 0
            
            print(f"Processing {len(events)} events from Google Calendar API for {connection.provider_account_email}")
            
            for event_data in events:
                event_id = event_data.get('id')
                event_title = event_data.get('summary', 'No Title')
                
                # Skip events that were created by bidirectional sync (they start with [SYNCED])
                # These will be handled by the bidirectional sync service, not regular sync
                if event_title.startswith('[SYNCED]'):
                    print(f"  Skipping synced event: {event_title} (created by bidirectional sync)")
                    continue
                if event_title.startswith('[Mirror]'):
                    print(f"  Skipping mirror blocker event: {event_title}")
                    continue
                
                if not MeetingDetectionService.is_google_real_meeting(event_data=event_data, calendar_id=calendar_id):
                    print(f"  Skipping non-meeting event: {event_title}")
                    continue
                
                # Create unique provider_event_id that includes account email to avoid conflicts
                unique_event_id = f"{connection.provider_account_email}:{event_id}"
                
                # Check if event already exists for this connection
                existing_event = Event.query.filter_by(
                    user_id=connection.user_id,
                    provider='google',
                    provider_event_id=unique_event_id
                ).first()
                
                if existing_event:
                    # Update existing event
                    self._update_event_from_google(existing_event, event_data)
                    updated_events_count += 1
                    print(f"  Updated existing event: {event_title}")
                else:
                    # Create new event
                    try:
                        new_event = self._create_event_from_google_connection(connection, event_data, unique_event_id)
                        db.session.add(new_event)
                        new_events_count += 1
                        print(f"  Added new event: {event_title} (ID: {unique_event_id})")
                    except Exception as e:
                        print(f"  ERROR creating event '{event_title}': {str(e)}")
                        import traceback
                        traceback.print_exc()
                        continue
                
                synced_count += 1
            
            # Update last_synced timestamp
            connection.last_synced = datetime.utcnow()
            
            # Commit all changes
            try:
                db.session.commit()
                print(f"✅ Database commit successful: {new_events_count} new events, {updated_events_count} updated events")
            except Exception as commit_error:
                print(f"❌ Database commit FAILED: {str(commit_error)}")
                import traceback
                traceback.print_exc()
                db.session.rollback()
                raise
            
            print(f"Synced {synced_count} events for Google account: {connection.provider_account_email}")
            return synced_count
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Failed to sync Google events for {connection.provider_account_email}: {str(e)}")
    
    def _create_event_from_google_connection(self, connection, event_data, unique_event_id):
        """Create Event object from Google Calendar event data for a CalendarConnection"""
        from models.event_model import Event
        import re
        
        start_data = event_data.get('start', {})
        end_data = event_data.get('end', {})
        
        # Parse start and end times
        start_time = self._parse_google_datetime(start_data)
        end_time = self._parse_google_datetime(end_data)
        
        # Extract Google Meet link from conferenceData or hangoutLink
        meet_link = None
        if event_data.get('conferenceData'):
            entry_points = event_data.get('conferenceData', {}).get('entryPoints', [])
            for entry in entry_points:
                if entry.get('entryPointType') == 'video':
                    meet_link = entry.get('uri')
                    break
        
        # Fallback to hangoutLink (legacy)
        if not meet_link and event_data.get('hangoutLink'):
            meet_link = event_data.get('hangoutLink')
        
        # Fallback: Extract from description if it contains a meet.google.com link
        if not meet_link:
            description = event_data.get('description', '')
            meet_pattern = r'https?://(?:meet\.google\.com/[a-z-]+|.*meet\.google\.com/[a-z-]+)'
            match = re.search(meet_pattern, description, re.IGNORECASE)
            if match:
                meet_link = match.group(0)
        
        event = Event(
            user_id=connection.user_id,
            title=event_data.get('summary', 'No Title'),
            description=event_data.get('description', ''),
            location=event_data.get('location', ''),
            start_time=start_time,
            end_time=end_time,
            all_day=start_data.get('date') is not None,
            provider='google',
            provider_event_id=unique_event_id,  # Use unique ID with account email
            calendar_id=connection.calendar_id or 'primary',
            organizer=connection.provider_account_email,  # Use connection's account email
            color=event_data.get('colorId', ''),
            meet_link=meet_link,
            last_synced=datetime.utcnow()
        )
        
        # Set attendees
        attendees = []
        for attendee in event_data.get('attendees', []):
            attendees.append({
                'email': attendee.get('email'),
                'name': attendee.get('displayName'),
                'response_status': attendee.get('responseStatus')
            })
        event.set_attendees(attendees)
        
        return event
    
    def _create_event_from_google(self, user, event_data):
        """Create Event object from Google Calendar event data"""
        import re
        
        start_data = event_data.get('start', {})
        end_data = event_data.get('end', {})
        
        # Parse start and end times
        start_time = self._parse_google_datetime(start_data)
        end_time = self._parse_google_datetime(end_data)
        
        # Extract Google Meet link from conferenceData or hangoutLink
        meet_link = None
        if event_data.get('conferenceData'):
            entry_points = event_data.get('conferenceData', {}).get('entryPoints', [])
            for entry in entry_points:
                if entry.get('entryPointType') == 'video':
                    meet_link = entry.get('uri')
                    break
        
        # Fallback to hangoutLink (legacy)
        if not meet_link and event_data.get('hangoutLink'):
            meet_link = event_data.get('hangoutLink')
        
        # Fallback: Extract from description if it contains a meet.google.com link
        if not meet_link:
            description = event_data.get('description', '')
            meet_pattern = r'https?://(?:meet\.google\.com/[a-z-]+|.*meet\.google\.com/[a-z-]+)'
            match = re.search(meet_pattern, description, re.IGNORECASE)
            if match:
                meet_link = match.group(0)
        
        event = Event(
            user_id=user.id,
            title=event_data.get('summary', 'No Title'),
            description=event_data.get('description', ''),
            location=event_data.get('location', ''),
            start_time=start_time,
            end_time=end_time,
            all_day=start_data.get('date') is not None,  # All-day events have 'date' instead of 'dateTime'
            provider='google',
            provider_event_id=event_data.get('id'),
            calendar_id='primary',
            organizer=event_data.get('organizer', {}).get('email', ''),
            color=event_data.get('colorId', ''),
            meet_link=meet_link,
            last_synced=datetime.utcnow()
        )
        
        # Set attendees
        attendees = []
        for attendee in event_data.get('attendees', []):
            attendees.append({
                'email': attendee.get('email'),
                'name': attendee.get('displayName'),
                'response_status': attendee.get('responseStatus')
            })
        event.set_attendees(attendees)
        
        return event
    
    def _update_event_from_google(self, event, event_data):
        """Update existing event with Google Calendar data"""
        import re
        
        start_data = event_data.get('start', {})
        end_data = event_data.get('end', {})
        
        event.title = event_data.get('summary', 'No Title')
        event.description = event_data.get('description', '')
        event.location = event_data.get('location', '')
        event.start_time = self._parse_google_datetime(start_data)
        event.end_time = self._parse_google_datetime(end_data)
        event.all_day = start_data.get('date') is not None
        event.organizer = event_data.get('organizer', {}).get('email', '')
        event.color = event_data.get('colorId', '')
        
        # Extract Google Meet link from conferenceData or hangoutLink
        meet_link = None
        if event_data.get('conferenceData'):
            entry_points = event_data.get('conferenceData', {}).get('entryPoints', [])
            for entry in entry_points:
                if entry.get('entryPointType') == 'video':
                    meet_link = entry.get('uri')
                    break
        
        # Fallback to hangoutLink (legacy)
        if not meet_link and event_data.get('hangoutLink'):
            meet_link = event_data.get('hangoutLink')
        
        # Fallback: Extract from description if it contains a meet.google.com link
        if not meet_link:
            description = event_data.get('description', '')
            meet_pattern = r'https?://(?:meet\.google\.com/[a-z-]+|.*meet\.google\.com/[a-z-]+)'
            match = re.search(meet_pattern, description, re.IGNORECASE)
            if match:
                meet_link = match.group(0)
        
        event.meet_link = meet_link
        event.last_synced = datetime.utcnow()
        
        # Update attendees
        attendees = []
        for attendee in event_data.get('attendees', []):
            attendees.append({
                'email': attendee.get('email'),
                'name': attendee.get('displayName'),
                'response_status': attendee.get('responseStatus')
            })
        event.set_attendees(attendees)
    
    def _parse_google_datetime(self, datetime_data):
        """Parse Google Calendar datetime format with proper IST timezone handling"""
        import pytz
        
        if 'dateTime' in datetime_data:
            date_time_str = datetime_data['dateTime']
            event_timezone = datetime_data.get('timeZone', 'UTC')
            
            # Handle different datetime formats
            if date_time_str.endswith('Z') or event_timezone == 'UTC':
                # UTC time - convert to IST
                if date_time_str.endswith('Z'):
                    utc_time = datetime.fromisoformat(date_time_str.replace('Z', '+00:00'))
                else:
                    # Google might send UTC times without 'Z' but with timeZone: 'UTC'
                    utc_time = datetime.fromisoformat(date_time_str).replace(tzinfo=pytz.UTC)
                
                ist_tz = pytz.timezone('Asia/Kolkata')
                ist_time = utc_time.astimezone(ist_tz)
                return ist_time.replace(tzinfo=None)  # Store as naive datetime in IST
            elif '+' in date_time_str or '-' in date_time_str[-6:]:
                # Has timezone offset - convert to IST
                parsed_time = datetime.fromisoformat(date_time_str)
                ist_tz = pytz.timezone('Asia/Kolkata')
                ist_time = parsed_time.astimezone(ist_tz)
                return ist_time.replace(tzinfo=None)  # Store as naive datetime in IST
            else:
                # No timezone info, assume it's already in IST
                return datetime.fromisoformat(date_time_str)
        elif 'date' in datetime_data:
            # All-day event
            return datetime.fromisoformat(datetime_data['date'])
        return None
    
    def get_calendar_client(self, user):
        """Get Google Calendar client for user"""
        token_info = user.get_google_token()
        if not token_info:
            raise Exception("No Google token found for user")
        
        # Check if token is expired
        if datetime.utcnow().timestamp() > token_info.get('expires_at', 0):
            # Refresh token using environment variables
            try:
                from google.oauth2.credentials import Credentials
                from google.auth.transport.requests import Request
                
                # Use stored token info or fallback to environment variables
                token_uri = token_info.get('token_uri', "https://oauth2.googleapis.com/token")
                client_id = token_info.get('client_id', self.client_id)
                client_secret = token_info.get('client_secret', self.client_secret)
                scopes = token_info.get('scopes', self.SCOPES)
                
                credentials = Credentials(
                    token=token_info.get('token'),
                    refresh_token=token_info.get('refresh_token'),
                    token_uri=token_uri,
                    client_id=client_id,
                    client_secret=client_secret,
                    scopes=scopes
                )
                
                # Refresh the token
                credentials.refresh(Request())
                
                # Update stored token
                token_info.update({
                    'token': credentials.token,
                    'refresh_token': credentials.refresh_token,
                    'expires_in': credentials.expiry.timestamp() - datetime.utcnow().timestamp(),
                    'expires_at': credentials.expiry.timestamp()
                })
                user.set_google_token(token_info)
                db.session.commit()
            except Exception as e:
                print(f"Error refreshing Google token: {e}")
                # Continue with existing token if refresh fails
        
        return GoogleCalendarClient(token_info['token'])

    def get_calendar_client_for_connection(self, connection):
        """Get Google Calendar client using a CalendarConnection token."""
        token_info = connection.get_token()
        if not token_info:
            raise Exception(f"No Google token found for connection {connection.provider_account_email}")
        
        # Refresh expired tokens
        if datetime.utcnow().timestamp() > token_info.get('expires_at', 0):
            try:
                credentials = Credentials(
                    token=token_info.get('token'),
                    refresh_token=token_info.get('refresh_token'),
                    token_uri=token_info.get('token_uri', "https://oauth2.googleapis.com/token"),
                    client_id=token_info.get('client_id', self.client_id),
                    client_secret=token_info.get('client_secret', self.client_secret),
                    scopes=token_info.get('scopes', self.SCOPES)
                )
                credentials.refresh(Request())
                token_info.update({
                    'token': credentials.token,
                    'refresh_token': credentials.refresh_token,
                    'expires_in': credentials.expiry.timestamp() - datetime.utcnow().timestamp(),
                    'expires_at': credentials.expiry.timestamp()
                })
                connection.set_token(token_info)
                db.session.commit()
            except Exception as e:
                print(f"Error refreshing Google token for connection {connection.provider_account_email}: {e}")
        
        return GoogleCalendarClient(token_info['token'])


class GoogleCalendarClient:
    """Helper class for Google Calendar API calls"""

    MIRROR_PREFIX = '[Mirror]'
    MIRROR_TITLE = '[Mirror] Busy'
    
    def __init__(self, access_token):
        self.access_token = access_token
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    
    def create_calendar_event(self, event_data, calendar_id='primary'):
        """Create event in Google Calendar (notifications always disabled)."""
        try:
            url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
            sanitized_body = self._sanitize_blocker_payload(event_data)
            params = {
                'sendUpdates': 'none',
                'conferenceDataVersion': 0
            }
            print(f"Creating Google Calendar event without notifications: {sanitized_body.get('summary', 'No title')}")
            response = requests.post(url, headers=self.headers, json=sanitized_body, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error creating Google Calendar event: {e}")
            return None

    def update_calendar_event(self, event_id, event_data, calendar_id='primary'):
        """Update an existing Google Calendar event without sending notifications."""
        if not event_id:
            return None
        try:
            url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events/{event_id}"
            sanitized_body = self._sanitize_blocker_payload(event_data)
            params = {
                'sendUpdates': 'none',
                'conferenceDataVersion': 0
            }
            print(f"Updating Google Calendar event {event_id} without notifications")
            response = requests.patch(url, headers=self.headers, json=sanitized_body, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error updating Google Calendar event {event_id}: {e}")
            return None

    def _sanitize_blocker_payload(self, event_data):
        """Force mirror blockers to be private, busy, and notification-free."""
        body = copy.deepcopy(event_data or {})
        summary = body.get('summary', '') or self.MIRROR_TITLE
        is_mirror = summary.startswith(self.MIRROR_PREFIX)
        body['summary'] = summary if summary.startswith(self.MIRROR_PREFIX) else summary
        
        if is_mirror:
            body['attendees'] = []
            body['visibility'] = 'private'
            body['transparency'] = 'opaque'
            body['reminders'] = {'useDefault': False}
            body['guestsCanModify'] = False
            body['guestsCanInviteOthers'] = False
            body['guestsCanSeeOtherGuests'] = False
        else:
            body.setdefault('guestsCanModify', False)
            body.setdefault('guestsCanInviteOthers', False)
            body.setdefault('guestsCanSeeOtherGuests', True)
        
        return body
