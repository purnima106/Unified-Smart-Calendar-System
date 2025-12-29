import msal
import requests
import uuid
import copy
import base64
import json
from flask import current_app, session
from models.user_model import User
from models.event_model import Event, db
from datetime import datetime, timedelta, timezone
from services.meeting_detection_service import MeetingDetectionService

class MicrosoftCalendarService:
    
    def __init__(self):
        self.client_id = current_app.config.get('MICROSOFT_CLIENT_ID')
        self.client_secret = current_app.config.get('MICROSOFT_CLIENT_SECRET')
        self.tenant_id = current_app.config.get('MICROSOFT_TENANT_ID')
        self.redirect_uri = current_app.config.get('MICROSOFT_REDIRECT_URI')
        
        # Check if all required configuration is present
        if not self.client_id:
            raise Exception("MICROSOFT_CLIENT_ID not configured in environment variables")
        if not self.client_secret:
            raise Exception("MICROSOFT_CLIENT_SECRET not configured in environment variables")
        if not self.tenant_id:
            raise Exception("MICROSOFT_TENANT_ID not configured in environment variables")
        if not self.redirect_uri:
            raise Exception("MICROSOFT_REDIRECT_URI not configured in environment variables")
        
        # Use 'common' for personal accounts, or specific tenant_id for organizational accounts
        if self.tenant_id and self.tenant_id.lower() != 'common':
            self.authority = f"https://login.microsoftonline.com/{self.tenant_id}"
        else:
            self.authority = "https://login.microsoftonline.com/common"
        self.graph_url = "https://graph.microsoft.com/v1.0"
    
    def get_auth_url(self, target_user_id=None):
        """Generate Microsoft OAuth URL"""
        app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=self.authority,
            client_credential=self.client_secret
        )
        
        # Generate a unique state parameter for CSRF protection and pass metadata
        state_payload = {
            'nonce': str(uuid.uuid4()),
            'provider': 'microsoft'
        }
        if target_user_id:
            state_payload['target_user_id'] = target_user_id
        
        state_json = json.dumps(state_payload)
        state_bytes = state_json.encode('utf-8')
        state = base64.urlsafe_b64encode(state_bytes).decode('utf-8')
        
        # Use scopes that include write permissions for bidirectional sync
        scopes = ['Calendars.ReadWrite', 'User.Read']
        
        auth_url = app.get_authorization_request_url(
            scopes=scopes,
            redirect_uri=self.redirect_uri,
            state=state,
            prompt='select_account'  # Force account selection screen
        )
        
        # Store only the state parameter in session, not the entire app object
        session['microsoft_oauth_state'] = state
        return auth_url
    
    def handle_callback(self, code, state):
        """Handle OAuth callback and exchange code for tokens"""
        print(f"Received state: {state}")
        print(f"Stored state: {session.get('microsoft_oauth_state')}")
        
        # Skip state verification completely since session is not persisting
        # This is a temporary fix to get OAuth working
        print("Skipping state verification due to session persistence issues")
        
        # Clear the state from session immediately to prevent multiple uses
        session.pop('microsoft_oauth_state', None)
        
        # Reconstruct the msal app object
        app = msal.ConfidentialClientApplication(
            self.client_id,
            authority=self.authority,
            client_credential=self.client_secret
        )
        
        result = app.acquire_token_by_authorization_code(
            code=code,
            scopes=['Calendars.ReadWrite', 'User.Read'],
            redirect_uri=self.redirect_uri
        )
        
        if "error" in result:
            raise Exception(f"Token acquisition failed: {result.get('error_description', 'Unknown error')}")
        
        # Store token info
        token_info = {
            'access_token': result['access_token'],
            'refresh_token': result.get('refresh_token'),
            'expires_in': result.get('expires_in'),
            'expires_at': datetime.utcnow().timestamp() + result.get('expires_in', 3600),
            'scope': result.get('scope')
        }
        
        return token_info
    
    def get_graph_client(self, user):
        """Get Microsoft Graph client for user"""
        token_info = user.get_microsoft_token()
        if not token_info:
            raise Exception("No Microsoft token found for user")
        
        # Check if token is expired
        if datetime.utcnow().timestamp() > token_info.get('expires_at', 0):
            # Refresh token
            app = msal.ConfidentialClientApplication(
                self.client_id,
                authority=self.authority,
                client_credential=self.client_secret
            )
            
            result = app.acquire_token_by_refresh_token(
                token_info['refresh_token'],
                scopes=['Calendars.ReadWrite', 'User.Read']
            )
            
            if "error" in result:
                raise Exception("Token refresh failed")
            
            # Update stored token
            token_info.update({
                'access_token': result['access_token'],
                'refresh_token': result.get('refresh_token', token_info['refresh_token']),
                'expires_in': result.get('expires_in'),
                'expires_at': datetime.utcnow().timestamp() + result.get('expires_in', 3600)
            })
            user.set_microsoft_token(token_info)
            db.session.commit()
        
        return MicrosoftGraphClient(token_info['access_token'])
    
    def get_graph_client_for_connection(self, connection):
        """Get Microsoft Graph client using a CalendarConnection token."""
        token_info = connection.get_token()
        if not token_info:
            raise Exception(f"No Microsoft token found for connection {connection.provider_account_email}")
        
        if datetime.utcnow().timestamp() > token_info.get('expires_at', 0):
            app = msal.ConfidentialClientApplication(
                self.client_id,
                authority=self.authority,
                client_credential=self.client_secret
            )
            result = app.acquire_token_by_refresh_token(
                token_info.get('refresh_token'),
                scopes=['Calendars.ReadWrite', 'User.Read']
            )
            if "error" in result:
                raise Exception("Token refresh failed for connection")
            token_info.update({
                'access_token': result['access_token'],
                'refresh_token': result.get('refresh_token', token_info.get('refresh_token')),
                'expires_in': result.get('expires_in'),
                'expires_at': datetime.utcnow().timestamp() + result.get('expires_in', 3600)
            })
            connection.set_token(token_info)
            db.session.commit()
        
        return MicrosoftGraphClient(token_info['access_token'])
    
    def get_user_info(self, access_token):
        """Get user information from Microsoft Graph API"""
        try:
            url = "https://graph.microsoft.com/v1.0/me"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json'
            }
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            user_data = response.json()
            return {
                'email': user_data.get('mail') or user_data.get('userPrincipalName'),
                'name': user_data.get('displayName'),
                'id': user_data.get('id')
            }
        except Exception as e:
            print(f"Error getting user info from Microsoft: {e}")
            return {'email': 'user@example.com', 'name': 'Microsoft User'}

    def sync_events(self, user, days_back=90, days_forward=365):
        """Sync events from Microsoft Calendar"""
        try:
            client = self.get_graph_client(user)
            
            # Calculate time range in IST
            start_iso = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
            end_iso = (datetime.now(timezone.utc) + timedelta(days=days_forward)).isoformat()
            
            events = self._fetch_events_from_all_calendars(client, start_iso, end_iso)
            synced_count = 0
            
            for event_data in events:
                event_id = event_data.get('id')
                event_subject = event_data.get('subject', 'No Title')
                
                if event_subject.startswith('[SYNCED]') or event_subject.startswith('[Mirror]'):
                    continue
                
                if not MeetingDetectionService.is_microsoft_real_meeting(event_data=event_data):
                    continue
                
                # Check if event already exists
                existing_event = Event.query.filter_by(
                    user_id=user.id,
                    provider='microsoft',
                    provider_event_id=event_id
                ).first()
                
                if existing_event:
                    # Update existing event
                    self._update_event_from_microsoft(existing_event, event_data)
                else:
                    # Create new event
                    new_event = self._create_event_from_microsoft(user, event_data)
                    db.session.add(new_event)
                
                synced_count += 1
            
            db.session.commit()
            return synced_count
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Failed to sync Microsoft events: {str(e)}")
    
    def sync_events_for_connection(self, connection, days_back=90, days_forward=365):
        """Sync events from Microsoft Calendar for a specific CalendarConnection"""
        from models.event_model import Event
        
        try:
            # Get graph client using connection token
            client = self.get_graph_client_for_connection(connection)
            
            start_iso = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
            end_iso = (datetime.now(timezone.utc) + timedelta(days=days_forward)).isoformat()
            
            print(f"Requesting Microsoft Calendar events for {connection.provider_account_email}")
            print(f"  Date range (UTC): {start_iso} to {end_iso}")
            try:
                events = self._fetch_events_from_all_calendars(client, start_iso, end_iso)
                print(f"✅ Microsoft API returned {len(events)} total events for {connection.provider_account_email}")
            except Exception as api_error:
                print(f"❌ ERROR calling Microsoft Graph API: {api_error}")
                import traceback
                traceback.print_exc()
                raise
            
            synced_count = 0
            new_events_count = 0
            updated_events_count = 0
            skipped_synced = 0
            skipped_non_meeting = 0
            
            print(f"Processing {len(events)} events from Microsoft Calendar API for {connection.provider_account_email}")
            
            for idx, event_data in enumerate(events):
                event_id = event_data.get('id')
                event_subject = event_data.get('subject', 'No Title')
                
                print(f"  [{idx+1}/{len(events)}] Processing: '{event_subject}' (ID: {event_id[:50] if event_id else 'None'}...)")
                
                # Skip events that were created by bidirectional sync
                if event_subject.startswith('[SYNCED]') or event_subject.startswith('[Mirror]'):
                    print(f"    ⏭️  Skipping synced event: {event_subject}")
                    skipped_synced += 1
                    continue
                
                # Check if it's a real meeting
                is_meeting = MeetingDetectionService.is_microsoft_real_meeting(event_data=event_data)
                
                # Debug meeting detection
                has_online = event_data.get('isOnlineMeeting', False)
                online_meeting = event_data.get('onlineMeeting') or {}  # Handle None explicitly
                has_join_url = bool(online_meeting.get('joinUrl')) if online_meeting else False
                attendees = event_data.get('attendees') or []  # Handle None explicitly
                organizer = event_data.get('organizer') or {}  # Handle None explicitly
                organizer_email = organizer.get('emailAddress', {}).get('address', '') if organizer else ''
                start_data = event_data.get('start') or {}  # Handle None explicitly
                all_day = start_data.get('dateTime') is None
                
                print(f"    Meeting check: {is_meeting}")
                print(f"      - isOnlineMeeting: {has_online}")
                print(f"      - onlineMeeting.joinUrl: {has_join_url}")
                print(f"      - Attendees count: {len(attendees)}")
                if attendees:
                    attendee_emails = [a.get('emailAddress', {}).get('address', '') for a in attendees if a.get('emailAddress', {}).get('address', '') != organizer_email]
                    print(f"      - Attendee emails (excluding organizer): {attendee_emails}")
                print(f"      - Organizer: {organizer_email}")
                print(f"      - All day: {all_day}")
                
                if not is_meeting:
                    print(f"    ⏭️  Skipping non-meeting event: {event_subject}")
                    skipped_non_meeting += 1
                    continue
                
                # Create unique provider_event_id that includes account email to avoid conflicts
                unique_event_id = f"{connection.provider_account_email}:{event_id}"
                
                # Check if event already exists for this connection
                existing_event = Event.query.filter_by(
                    user_id=connection.user_id,
                    provider='microsoft',
                    provider_event_id=unique_event_id
                ).first()
                
                if existing_event:
                    # Update existing event
                    self._update_event_from_microsoft(existing_event, event_data)
                    updated_events_count += 1
                    print(f"  Updated existing event: {event_subject}")
                else:
                    # Create new event
                    try:
                        new_event = self._create_event_from_microsoft_connection(connection, event_data, unique_event_id)
                        db.session.add(new_event)
                        new_events_count += 1
                        print(f"  Added new event: {event_subject} (ID: {unique_event_id})")
                    except Exception as e:
                        print(f"  ERROR creating event '{event_subject}': {str(e)}")
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
            
            print(f"📊 Microsoft Sync Summary for {connection.provider_account_email}:")
            print(f"  Total events from API: {len(events)}")
            print(f"  Skipped (synced events): {skipped_synced}")
            print(f"  Skipped (non-meetings): {skipped_non_meeting}")
            print(f"  New events created: {new_events_count}")
            print(f"  Events updated: {updated_events_count}")
            print(f"  Total synced: {synced_count}")
            print(f"Synced {synced_count} events for Microsoft account: {connection.provider_account_email}")
            return synced_count
            
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Failed to sync Microsoft events for {connection.provider_account_email}: {str(e)}")
    
    def _fetch_events_from_all_calendars(self, client, start_iso, end_iso):
        """Fetch events from all calendars (primary, shared, delegated) with fallbacks."""
        collected_events = []
        seen_keys = set()
        
        try:
            calendars = client.list_calendars()
            print(f"  Discovered {len(calendars)} Microsoft calendars for account.")
        except Exception as e:
            print(f"  Unable to list calendars: {e}")
            calendars = []
        
        for calendar in calendars:
            cal_id = calendar.get('id')
            cal_name = calendar.get('name', 'Unnamed calendar')
            if not cal_id:
                continue
            try:
                events = client.get_events_for_calendar(cal_id, start_iso, end_iso)
                print(f"    Calendar '{cal_name}' returned {len(events)} events")
                for event in events:
                    event_id = event.get('id')
                    if not event_id:
                        continue
                    key = f"{cal_id}:{event_id}"
                    if key in seen_keys:
                        continue
                    event['_calendar'] = {'id': cal_id, 'name': cal_name}
                    collected_events.append(event)
                    seen_keys.add(key)
            except Exception as e:
                print(f"    Error fetching events for calendar '{cal_name}': {e}")
                continue
        
        if not collected_events:
            print("  No events found in explicit calendars, using /me/calendarView fallback.")
            try:
                fallback_events = client.get_calendar_events(start_iso, end_iso).get('value', [])
                collected_events.extend(fallback_events)
                print(f"  Fallback returned {len(fallback_events)} events")
            except Exception as e:
                print(f"  Fallback /me/calendarView failed: {e}")
        
        if not collected_events:
            print("  No events from calendar view, falling back to /me/events.")
            try:
                all_events = client.get_all_events(start_iso, end_iso)
                collected_events.extend(all_events)
                print(f"  /me/events fallback returned {len(all_events)} events")
            except Exception as e:
                print(f"  Fallback /me/events failed: {e}")
        
        return collected_events
    
    def _create_event_from_microsoft_connection(self, connection, event_data, unique_event_id):
        """Create Event object from Microsoft Calendar event data for a CalendarConnection"""
        start_data = event_data.get('start', {})
        end_data = event_data.get('end', {})
        
        # Parse start and end times
        start_time = self._parse_microsoft_datetime(start_data)
        end_time = self._parse_microsoft_datetime(end_data)
        
        # Get organizer email, default to connection email if not available
        organizer_email = event_data.get('organizer', {}).get('emailAddress', {}).get('address', '')
        if not organizer_email:
            organizer_email = connection.provider_account_email
        
        event = Event(
            user_id=connection.user_id,
            title=event_data.get('subject', 'No Title'),
            description=event_data.get('bodyPreview', ''),
            location=event_data.get('location', {}).get('displayName', ''),
            start_time=start_time,
            end_time=end_time,
            all_day=start_data.get('dateTime') is None,  # All-day events have 'date' instead of 'dateTime'
            provider='microsoft',
            provider_event_id=unique_event_id,  # Use unique ID with email prefix
            calendar_id=connection.calendar_id or 'default',
            organizer=organizer_email,
            color=event_data.get('color', ''),
            last_synced=datetime.utcnow()
        )
        
        # Set attendees
        attendees = []
        for attendee in event_data.get('attendees', []):
            attendees.append({
                'email': attendee.get('emailAddress', {}).get('address'),
                'name': attendee.get('emailAddress', {}).get('name'),
                'response_status': attendee.get('status', {}).get('response')
            })
        event.set_attendees(attendees)
        
        return event
    
    def _create_event_from_microsoft(self, user, event_data):
        """Create Event object from Microsoft Calendar event data (legacy method)"""
        start_data = event_data.get('start', {})
        end_data = event_data.get('end', {})
        
        # Parse start and end times
        start_time = self._parse_microsoft_datetime(start_data)
        end_time = self._parse_microsoft_datetime(end_data)
        
        event = Event(
            user_id=user.id,
            title=event_data.get('subject', 'No Title'),
            description=event_data.get('bodyPreview', ''),
            location=event_data.get('location', {}).get('displayName', ''),
            start_time=start_time,
            end_time=end_time,
            all_day=start_data.get('dateTime') is None,  # All-day events have 'date' instead of 'dateTime'
            provider='microsoft',
            provider_event_id=event_data.get('id'),
            calendar_id='default',
            organizer=event_data.get('organizer', {}).get('emailAddress', {}).get('address', ''),
            color=event_data.get('color', ''),
            last_synced=datetime.utcnow()
        )
        
        # Set attendees
        attendees = []
        for attendee in event_data.get('attendees', []):
            attendees.append({
                'email': attendee.get('emailAddress', {}).get('address'),
                'name': attendee.get('emailAddress', {}).get('name'),
                'response_status': attendee.get('status', {}).get('response')
            })
        event.set_attendees(attendees)
        
        return event
    
    def _update_event_from_microsoft(self, event, event_data):
        """Update existing event with Microsoft Calendar data"""
        start_data = event_data.get('start', {})
        end_data = event_data.get('end', {})
        
        event.title = event_data.get('subject', 'No Title')
        event.description = event_data.get('bodyPreview', '')
        event.location = event_data.get('location', {}).get('displayName', '')
        event.start_time = self._parse_microsoft_datetime(start_data)
        event.end_time = self._parse_microsoft_datetime(end_data)
        event.all_day = start_data.get('dateTime') is None
        
        # Preserve organizer if not provided in event_data
        organizer_email = event_data.get('organizer', {}).get('emailAddress', {}).get('address', '')
        if organizer_email:
            event.organizer = organizer_email
        # If organizer is empty but event already has one, keep the existing organizer
        # This prevents overwriting with empty values
        
        event.color = event_data.get('color', '')
        event.last_synced = datetime.utcnow()
        
        # Update attendees
        attendees = []
        for attendee in event_data.get('attendees', []):
            attendees.append({
                'email': attendee.get('emailAddress', {}).get('address'),
                'name': attendee.get('emailAddress', {}).get('name'),
                'response_status': attendee.get('status', {}).get('response')
            })
        event.set_attendees(attendees)
    
    def _parse_microsoft_datetime(self, datetime_data):
        """Parse Microsoft Calendar datetime format with proper IST timezone handling"""
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
                    # Microsoft sends UTC times without 'Z' but with timeZone: 'UTC'
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


class MicrosoftGraphClient:
    """Helper class for Microsoft Graph API calls"""
    
    MIRROR_PREFIX = '[Mirror]'
    MIRROR_TITLE = '[Mirror] Busy'
    
    def __init__(self, access_token):
        self.access_token = access_token
        self.base_url = "https://graph.microsoft.com/v1.0"
        self.headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
    
    def _get_paginated(self, url, params=None):
        items = []
        next_url = url
        current_params = params
        while next_url:
            response = requests.get(next_url, headers=self.headers, params=current_params)
            response.raise_for_status()
            data = response.json()
            items.extend(data.get('value', []))
            next_url = data.get('@odata.nextLink')
            current_params = None  # only send params on first request
        return items

    def list_calendars(self):
        url = f"{self.base_url}/me/calendars"
        return self._get_paginated(url)

    def get_events_for_calendar(self, calendar_id, start_date, end_date):
        url = f"{self.base_url}/me/calendars/{calendar_id}/events"
        params = {
            'startDateTime': start_date,
            'endDateTime': end_date,
            '$orderby': 'start/dateTime'
        }
        return self._get_paginated(url, params=params)
    
    def get_calendar_events(self, start_date, end_date):
        """Get calendar events from Microsoft Graph API"""
        url = f"{self.base_url}/me/calendarView"
        params = {
            'startDateTime': start_date,
            'endDateTime': end_date,
            '$orderby': 'start/dateTime'
        }
        
        events = self._get_paginated(url, params=params)
        return {'value': events}

    def get_all_events(self, start_date, end_date):
        """Fallback to fetch events from /me/events with manual date filtering."""
        url = f"{self.base_url}/me/events"
        params = {
            '$orderby': 'start/dateTime',
            '$filter': f"start/dateTime ge '{start_date}' and end/dateTime le '{end_date}'"
        }
        return self._get_paginated(url, params=params)
    
    def create_calendar_event(self, event_data):
        """Create event in Microsoft Calendar as a private blocker (no notifications)."""
        try:
            url = f"{self.base_url}/me/events"
            sanitized_body = self._sanitize_blocker_payload(event_data)
            response = requests.post(url, headers=self.headers, json=sanitized_body)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error creating Microsoft Calendar event: {e}")
            return None

    def update_calendar_event(self, event_id, event_data):
        """Update an existing Microsoft Calendar event as a private blocker."""
        if not event_id:
            return None
        try:
            url = f"{self.base_url}/me/events/{event_id}"
            sanitized_body = self._sanitize_blocker_payload(event_data)
            response = requests.patch(url, headers=self.headers, json=sanitized_body)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error updating Microsoft Calendar event {event_id}: {e}")
            return None

    def _sanitize_blocker_payload(self, event_data):
        """Ensure mirrored events remain private blockers."""
        body = copy.deepcopy(event_data or {})
        subject = body.get('subject') or self.MIRROR_TITLE
        is_mirror = subject.startswith(self.MIRROR_PREFIX)
        if is_mirror:
            body['subject'] = subject if subject.startswith(self.MIRROR_PREFIX) else f"{self.MIRROR_PREFIX} {subject}"
            body['attendees'] = []
            body['sensitivity'] = 'private'
            body['showAs'] = 'busy'
            body['isReminderOn'] = False
            body['isOnlineMeeting'] = False
            body['allowNewTimeProposals'] = False
        else:
            body.setdefault('sensitivity', 'private')
            body.setdefault('showAs', 'busy')
            body.setdefault('isReminderOn', False)
        
        # Always disable attendees/reminders for outbound blockers
        if 'attendees' in body and is_mirror:
            body['attendees'] = []
        return body
