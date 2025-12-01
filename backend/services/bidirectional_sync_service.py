#!/usr/bin/env python3
"""
Bidirectional Calendar Sync Service
Creates events from one calendar system in the other calendar system
Supports:
- Google ↔ Microsoft sync
- Google ↔ Google sync (multi-account)
"""

import pytz
from datetime import datetime, timedelta
from models.user_model import User, db
from models.event_model import Event
from models.calendar_connection_model import CalendarConnection
from models.event_mirror_mapping_model import EventMirrorMapping
from services.google_service import GoogleCalendarService
from services.microsoft_service import MicrosoftCalendarService
from services.meeting_detection_service import MeetingDetectionService

class BidirectionalSyncService:
    """Service to sync events bidirectionally between Google and Microsoft calendars, and between multiple Google accounts"""
    
    MIRROR_TITLE = '[Mirror] Busy'
    
    def __init__(self):
        self.google_service = GoogleCalendarService()
        self.microsoft_service = MicrosoftCalendarService()
        self.ist_tz = pytz.timezone('Asia/Kolkata')
    
    def sync_bidirectional(self, days_back=30, days_forward=30, send_notifications=False):
        """Sync events bidirectionally between:
        - Google and Microsoft calendars
        - Multiple Google accounts (Google ↔ Google)
        - Multiple Microsoft accounts (Microsoft ↔ Microsoft)
        """
        try:
            print("Starting bidirectional sync...")
            print(f"Bidirectional sync: NEVER sending notifications (this is just mirroring existing events)")
            
            # Get all connections (multi-account support)
            google_connections = CalendarConnection.query.filter_by(
                provider='google',
                is_active=True,
                is_connected=True
            ).all()
            microsoft_connections = CalendarConnection.query.filter_by(
                provider='microsoft',
                is_active=True,
                is_connected=True
            ).all()
            
            # Group connections by owning user to avoid cross-user syncing
            google_connections_by_user = {}
            for connection in google_connections:
                google_connections_by_user.setdefault(connection.user_id, []).append(connection)
            
            microsoft_connections_by_user = {}
            for connection in microsoft_connections:
                microsoft_connections_by_user.setdefault(connection.user_id, []).append(connection)
            
            # Fallback to legacy User model if no CalendarConnection records exist
            legacy_users = []
            if not google_connections and not microsoft_connections:
                legacy_users = User.query.filter(
                    (User.google_calendar_connected == True) | 
                    (User.microsoft_calendar_connected == True)
                ).all()
            
            if not google_connections and not microsoft_connections and not legacy_users:
                print("No users with connected calendars found")
                return {
                    'google_to_microsoft': 0,
                    'microsoft_to_google': 0,
                    'google_to_google': 0,
                    'microsoft_to_microsoft': 0,
                    'users_processed': 0
                }
            
            total_google_to_microsoft = 0
            total_microsoft_to_google = 0
            total_google_to_google = 0
            total_microsoft_to_microsoft = 0
            
            # Get events from the last sync period
            start_date = datetime.now(self.ist_tz) - timedelta(days=days_back)
            end_date = datetime.now(self.ist_tz) + timedelta(days=days_forward)
            
            print(f"Date range: {start_date} to {end_date}")
            
            # Get all events within range and group by user
            all_events = Event.query.filter(
                Event.start_time >= start_date,
                Event.start_time <= end_date
            ).all()
            print(f"Total events in date range: {len(all_events)}")
            google_events = [e for e in all_events if e.provider == 'google']
            microsoft_events = [e for e in all_events if e.provider == 'microsoft']
            
            events_by_user = {}
            for event in all_events:
                events_by_user.setdefault(event.user_id, []).append(event)
            
            processed_user_ids = set(google_connections_by_user.keys()) | set(microsoft_connections_by_user.keys())
            
            for user_id in processed_user_ids:
                user_events = events_by_user.get(user_id, [])
                user_google_events = [e for e in user_events if e.provider == 'google']
                user_microsoft_events = [e for e in user_events if e.provider == 'microsoft']
                
                user_google_connections = google_connections_by_user.get(user_id, [])
                user_microsoft_connections = microsoft_connections_by_user.get(user_id, [])
                
                # Google ↔ Google sync per user
                if len(user_google_connections) > 1 and user_google_events:
                    try:
                        synced_count = self._sync_google_to_google(user_google_connections, user_google_events, send_notifications=False)
                        total_google_to_google += synced_count
                        print(f"[User {user_id}] Synced {synced_count} events between Google accounts")
                    except Exception as e:
                        print(f"[User {user_id}] Error syncing Google to Google: {e}")
                        import traceback
                        traceback.print_exc()
                
                # Microsoft ↔ Microsoft sync per user
                if len(user_microsoft_connections) > 1 and user_microsoft_events:
                    try:
                        synced_count = self._sync_microsoft_to_microsoft(user_microsoft_connections, user_microsoft_events, send_notifications=False)
                        total_microsoft_to_microsoft += synced_count
                        print(f"[User {user_id}] Synced {synced_count} events between Microsoft accounts")
                    except Exception as e:
                        print(f"[User {user_id}] Error syncing Microsoft to Microsoft: {e}")
                        import traceback
                        traceback.print_exc()
                
                # Google → Microsoft for each Microsoft connection owned by the user
                if user_microsoft_connections and user_google_events:
                    for connection in user_microsoft_connections:
                        try:
                            synced_count = self._sync_google_to_microsoft(connection, user_google_events, send_notifications=False)
                            total_google_to_microsoft += synced_count
                            if synced_count:
                                print(f"[User {user_id}] Synced {synced_count} Google events to Microsoft account {connection.provider_account_email}")
                        except Exception as e:
                            print(f"[User {user_id}] Error syncing Google to Microsoft for {connection.provider_account_email}: {e}")
                
                # Microsoft → Google for each Google connection owned by the user
                if user_google_connections and user_microsoft_events:
                    for connection in user_google_connections:
                        try:
                            synced_count = self._sync_microsoft_to_google(connection, user_microsoft_events, send_notifications=False)
                            total_microsoft_to_google += synced_count
                            if synced_count:
                                print(f"[User {user_id}] Synced {synced_count} Microsoft events to Google account {connection.provider_account_email}")
                        except Exception as e:
                            print(f"[User {user_id}] Error syncing Microsoft to Google for {connection.provider_account_email}: {e}")
            
            # Legacy support: If using old User model
            if legacy_users and not google_connections and not microsoft_connections:
                microsoft_users = [u for u in legacy_users if u.microsoft_calendar_connected]
                if microsoft_users and google_events:
                    try:
                        microsoft_user = microsoft_users[0]
                        synced_count = self._sync_google_to_microsoft(microsoft_user, google_events, send_notifications=False)
                        total_google_to_microsoft += synced_count
                    except Exception as e:
                        print(f"Error syncing Google to Microsoft (legacy): {e}")
                
                google_users = [u for u in legacy_users if u.google_calendar_connected]
                if google_users and microsoft_events:
                    try:
                        google_user = google_users[0]
                        synced_count = self._sync_microsoft_to_google(google_user, microsoft_events, send_notifications=False)
                        total_microsoft_to_google += synced_count
                    except Exception as e:
                        print(f"Error syncing Microsoft to Google (legacy): {e}")
            
            print(f"Bidirectional sync completed:")
            print(f"  Google → Microsoft: {total_google_to_microsoft} events")
            print(f"  Microsoft → Google: {total_microsoft_to_google} events")
            print(f"  Google → Google: {total_google_to_google} events")
            print(f"  Microsoft → Microsoft: {total_microsoft_to_microsoft} events")
            print(f"  Note: NO notifications sent (this is just mirroring existing events)")
            
            return {
                'google_to_microsoft': total_google_to_microsoft,
                'microsoft_to_google': total_microsoft_to_google,
                'google_to_google': total_google_to_google,
                'microsoft_to_microsoft': total_microsoft_to_microsoft,
                'users_processed': len(processed_user_ids) if processed_user_ids else len(legacy_users)
            }
            
        except Exception as e:
            print(f"Bidirectional sync error: {e}")
            import traceback
            traceback.print_exc()
            raise
    
    def _sync_google_to_microsoft(self, target, google_events, send_notifications=True):
        """Mirror real Google meetings into Microsoft as private blockers (connection or legacy user)."""
        synced_count = 0
        connection = None
        user = None
        calendar_id = 'default'
        if isinstance(target, CalendarConnection):
            connection = target
            user_id = connection.user_id
            target_email = connection.provider_account_email
            calendar_id = connection.calendar_id or 'default'
            get_client = lambda: self.microsoft_service.get_graph_client_for_connection(connection)
        else:
            user = target
            user_id = user.id
            target_email = user.email
            get_client = lambda: self.microsoft_service.get_graph_client(user)
        try:
            client = get_client()
        except Exception as auth_error:
            print(f"    Unable to get Microsoft Graph client for {target_email}: {auth_error}")
            return 0
        
        for event in google_events:
            try:
                if not self._should_sync_google_event(event):
                    continue
                
                mapping = self._find_mapping(
                    user_id=user_id,
                    original_provider='google',
                    original_provider_event_id=event.provider_event_id,
                    mirror_provider='microsoft',
                    mirror_account_email=target_email
                )
                blocker_payload = self._build_microsoft_blocker_payload(event)

                if mapping:
                    updated = client.update_calendar_event(mapping.mirror_provider_event_id, blocker_payload)
                    if updated:
                        self._update_local_blocker(mapping, event)
                        synced_count += 1
                    continue
                
                response = client.create_calendar_event(blocker_payload)
                if response:
                    remote_id = response.get('id', f"mirror_ms_{event.id}")
                    mirror_event = self._create_local_blocker_event(
                        user_id=user_id,
                        provider='microsoft',
                        provider_event_id=remote_id,
                        start_time=event.start_time,
                        end_time=event.end_time,
                        all_day=event.all_day,
                        calendar_id=calendar_id,
                        organizer=target_email
                    )

                    mapping = EventMirrorMapping(
                        user_id=user_id,
                        original_provider='google',
                        original_event_id=event.id,
                        original_provider_event_id=event.provider_event_id or f"google_local_{event.id}",
                        mirror_provider='microsoft',
                        mirror_event_id=mirror_event.id,
                        mirror_provider_event_id=remote_id
                    )
                    db.session.add(mapping)
                    synced_count += 1
                
            except Exception as e:
                print(f"    Error syncing event '{event.title}' to Microsoft: {e}")
                continue
        
        db.session.commit()
        return synced_count
    
    def _sync_microsoft_to_google(self, target, microsoft_events, send_notifications=True):
        """Mirror real Microsoft meetings into Google as private blockers (connection or legacy user)."""
        synced_count = 0
        connection = None
        user = None
        if isinstance(target, CalendarConnection):
            connection = target
            user_id = connection.user_id
            target_email = connection.provider_account_email
            calendar_id = connection.calendar_id or 'primary'
            get_client = lambda: self.google_service.get_calendar_client_for_connection(connection)
        else:
            user = target
            user_id = user.id
            target_email = user.email
            calendar_id = 'primary'
            get_client = lambda: self.google_service.get_calendar_client(user)
        try:
            client = get_client()
        except Exception as auth_error:
            print(f"    Unable to get Google Calendar client for {target_email}: {auth_error}")
            return 0
        
        for event in microsoft_events:
            try:
                if not self._should_sync_microsoft_event(event):
                    continue
                
                mapping = self._find_mapping(
                    user_id=user_id,
                    original_provider='microsoft',
                    original_provider_event_id=event.provider_event_id,
                    mirror_provider='google',
                    mirror_account_email=target_email
                )
                blocker_payload = self._build_google_blocker_payload(event)

                if mapping:
                    updated = client.update_calendar_event(mapping.mirror_provider_event_id, blocker_payload, calendar_id=calendar_id)
                    if updated:
                        self._update_local_blocker(mapping, event)
                        synced_count += 1
                    continue
                
                response = client.create_calendar_event(blocker_payload, calendar_id=calendar_id)
                if response:
                    provider_event_id = response.get('id', f"mirror_google_{event.id}")
                    unique_event_id = f"{target_email}:{provider_event_id}"
                    mirror_event = self._create_local_blocker_event(
                        user_id=user_id,
                        provider='google',
                        provider_event_id=unique_event_id,
                        start_time=event.start_time,
                        end_time=event.end_time,
                        all_day=event.all_day,
                        calendar_id=calendar_id,
                        organizer=target_email
                    )
                    
                    mapping = EventMirrorMapping(
                        user_id=user_id,
                        original_provider='microsoft',
                        original_event_id=event.id,
                        original_provider_event_id=event.provider_event_id or f"microsoft_local_{event.id}",
                        mirror_provider='google',
                        mirror_event_id=mirror_event.id,
                        mirror_provider_event_id=mirror_event.provider_event_id
                    )
                    db.session.add(mapping)
                    synced_count += 1
                
            except Exception as e:
                print(f"    Error syncing event '{event.title}' to Google: {e}")
                continue
        
        db.session.commit()
        return synced_count
    
    def _sync_google_to_google(self, google_connections, google_events, send_notifications=False):
        """Mirror real meetings between multiple Google accounts as private blockers."""
        synced_count = 0
        
        if len(google_connections) < 2:
            print("Need at least 2 Google accounts for Google-to-Google sync")
            return 0
        
        print(f"Syncing events between {len(google_connections)} Google accounts...")
        
        # Group events by source account (extract email from provider_event_id or organizer)
        events_by_account = {}
        for event in google_events:
            if not self._should_sync_google_event(event):
                continue
            source_account = None
            if event.provider_event_id and ':' in event.provider_event_id:
                source_account = event.provider_event_id.split(':')[0]
            elif event.organizer:
                source_account = event.organizer
            
            if source_account:
                events_by_account.setdefault(source_account, []).append(event)
        
        print(f"Events grouped by account: {[(acc, len(evts)) for acc, evts in events_by_account.items()]}")
        
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        
        for target_connection in google_connections:
            target_email = target_connection.provider_account_email
            print(f"\nSyncing events TO account: {target_email}")
            
            # Build calendar service for the target connection
            token_info = target_connection.get_token()
            if not token_info:
                print(f"  No token for {target_email}, skipping")
                continue
            
            credentials = Credentials(
                token=token_info['token'],
                refresh_token=token_info.get('refresh_token'),
                token_uri=token_info.get('token_uri', 'https://oauth2.googleapis.com/token'),
                client_id=token_info.get('client_id', self.google_service.client_id),
                client_secret=token_info.get('client_secret', self.google_service.client_secret),
                scopes=token_info.get('scopes', self.google_service.SCOPES)
            )
            
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                token_info['token'] = credentials.token
                target_connection.set_token(token_info)
                db.session.commit()
            
            service = build('calendar', 'v3', credentials=credentials)
            calendar_id = target_connection.calendar_id or 'primary'
            
            # Collect events from other accounts
            events_to_sync = []
            for source_account, events in events_by_account.items():
                if source_account != target_email:
                    events_to_sync.extend(events)
            
            if not events_to_sync:
                print(f"  No events to sync to {target_email}")
                continue
            
            print(f"  Preparing {len(events_to_sync)} events for {target_email}")
            
            for event in events_to_sync:
                try:
                    mapping = self._find_mapping(
                        user_id=target_connection.user_id,
                        original_provider='google',
                        original_provider_event_id=event.provider_event_id,
                        mirror_provider='google',
                        mirror_account_email=target_email
                    )
                    blocker_payload = self._build_google_blocker_payload(event)
                    
                    if mapping:
                        updated = self._update_google_calendar_event(service, calendar_id, mapping.mirror_provider_event_id, blocker_payload)
                        if updated:
                            self._update_local_blocker(mapping, event)
                            synced_count += 1
                        continue
                    
                    created_event = self._insert_google_blocker_event(service, calendar_id, blocker_payload)
                    if created_event:
                        remote_event_id = created_event.get('id')
                        unique_event_id = f"{target_email}:{remote_event_id}"
                        mirror_event = self._create_local_blocker_event(
                            user_id=target_connection.user_id,
                            provider='google',
                            provider_event_id=unique_event_id,
                            start_time=event.start_time,
                            end_time=event.end_time,
                            all_day=event.all_day,
                            calendar_id=calendar_id,
                            organizer=target_email
                        )
                        
                        mapping = EventMirrorMapping(
                            user_id=target_connection.user_id,
                            original_provider='google',
                            original_event_id=event.id,
                            original_provider_event_id=event.provider_event_id or f"google_local_{event.id}",
                            mirror_provider='google',
                            mirror_event_id=mirror_event.id,
                            mirror_provider_event_id=remote_event_id
                        )
                        db.session.add(mapping)
                        synced_count += 1
                
                except Exception as e:
                    print(f"    ❌ Error syncing event '{event.title}' to {target_email}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
        
        db.session.commit()
        return synced_count

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------
    def _should_sync_google_event(self, event: Event) -> bool:
        """Filter out mirrored/synced entries and ensure event is a real meeting."""
        if not event:
            return False
        title = (event.title or '').lower()
        if title.startswith('[synced]') or title.startswith('[mirror]'):
            return False
        return MeetingDetectionService.is_google_real_meeting(event=event)

    def _should_sync_microsoft_event(self, event: Event) -> bool:
        """Filter out mirrored/synced Microsoft entries and ensure they represent real meetings."""
        if not event:
            return False
        title = (event.title or '').lower()
        if title.startswith('[synced]') or title.startswith('[mirror]'):
            return False
        return MeetingDetectionService.is_microsoft_real_meeting(event=event)

    def _build_microsoft_blocker_payload(self, event: Event) -> dict:
        """Construct Microsoft blocker event body with actual event title."""
        return {
            'subject': event.title or 'Busy',  # Use actual event title instead of [Mirror] Busy
            'start': {
                'dateTime': self._format_datetime(event.start_time),
                'timeZone': 'Asia/Kolkata'
            },
            'end': {
                'dateTime': self._format_datetime(event.end_time),
                'timeZone': 'Asia/Kolkata'
            },
            'sensitivity': 'private',
            'showAs': 'busy',
            'isReminderOn': False,
            'attendees': [],
            'isOnlineMeeting': False,
            'allowNewTimeProposals': False,
        }

    def _build_google_blocker_payload(self, event: Event) -> dict:
        """Construct Google blocker event body with actual event title."""
        return {
            'summary': event.title or 'Busy',  # Use actual event title instead of [Mirror] Busy
            'start': {
                'dateTime': self._format_datetime(event.start_time),
                'timeZone': 'Asia/Kolkata'
            },
            'end': {
                'dateTime': self._format_datetime(event.end_time),
                'timeZone': 'Asia/Kolkata'
            },
            'visibility': 'private',
            'transparency': 'opaque',
            'attendees': [],
            'reminders': {'useDefault': False},
            'guestsCanModify': False,
            'guestsCanInviteOthers': False,
            'guestsCanSeeOtherGuests': False,
        }

    def _create_local_blocker_event(self, user_id, provider, provider_event_id, start_time, end_time, all_day, calendar_id, organizer=''):
        """Persist mirrored blocker event in the unified events table."""
        mirror_event = Event(
            user_id=user_id,
            title=self.MIRROR_TITLE,
            description='',
            location='',
            start_time=start_time,
            end_time=end_time,
            all_day=all_day,
            provider=provider,
            provider_event_id=provider_event_id,
            calendar_id=calendar_id,
            organizer=organizer or '',
            last_synced=datetime.utcnow()
        )
        mirror_event.set_attendees([])
        db.session.add(mirror_event)
        db.session.flush()
        return mirror_event

    def _update_local_blocker(self, mapping: EventMirrorMapping, source_event: Event):
        """Update mirrored blocker times when the original meeting changes."""
        if not mapping:
            return
        mirror_event = None
        if mapping.mirror_event_id:
            mirror_event = Event.query.get(mapping.mirror_event_id)
        if not mirror_event and mapping.mirror_provider_event_id:
            mirror_event = Event.query.filter_by(
                provider=mapping.mirror_provider,
                provider_event_id=mapping.mirror_provider_event_id
            ).first()
        if not mirror_event and mapping.mirror_provider_event_id:
            mirror_event = Event.query.filter(
                Event.provider == mapping.mirror_provider,
                Event.provider_event_id.like(f"%{mapping.mirror_provider_event_id}")
            ).first()
        if not mirror_event:
            return
        mirror_event.start_time = source_event.start_time
        mirror_event.end_time = source_event.end_time
        mirror_event.all_day = source_event.all_day
        mirror_event.last_synced = datetime.utcnow()

    @staticmethod
    def _insert_google_blocker_event(service, calendar_id, body):
        """Create a Google blocker event via Calendar API with notifications disabled."""
        try:
            return service.events().insert(
                calendarId=calendar_id,
                body=body,
                sendUpdates='none',
                conferenceDataVersion=0
            ).execute()
        except Exception as e:
            print(f"    Error creating Google blocker event: {e}")
            return None

    @staticmethod
    def _update_google_calendar_event(service, calendar_id, event_id, body):
        """Update an existing Google blocker event."""
        if not event_id:
            return False
        try:
            service.events().patch(
                calendarId=calendar_id,
                eventId=event_id,
                body=body,
                sendUpdates='none',
                conferenceDataVersion=0
            ).execute()
            return True
        except Exception as e:
            print(f"    Error updating Google blocker event {event_id}: {e}")
            return False

    @staticmethod
    def _find_mapping(user_id, original_provider, original_provider_event_id, mirror_provider, mirror_account_email=None):
        if not original_provider_event_id:
            return None
        query = EventMirrorMapping.query.filter_by(
            user_id=user_id,
            original_provider=original_provider,
            original_provider_event_id=original_provider_event_id,
            mirror_provider=mirror_provider
        )
        if not mirror_account_email:
            return query.first()
        mappings = query.all()
        for mapping in mappings:
            if mapping.mirror_event_id:
                mirror_event = Event.query.get(mapping.mirror_event_id)
                if mirror_event and mirror_event.organizer == mirror_account_email:
                    return mapping
        # Fall back to the first mapping (if any) even if the organizer check failed.
        # This prevents attempting to insert a duplicate mapping and triggering the
        # unique constraint error when the mirror event was deleted or organizer changed.
        return mappings[0] if mappings else None

    def _sync_microsoft_to_microsoft(self, microsoft_connections, microsoft_events, send_notifications=False):
        """Mirror real meetings between multiple Microsoft accounts as private blockers."""
        synced_count = 0
        
        if len(microsoft_connections) < 2:
            print("Need at least 2 Microsoft accounts for Microsoft-to-Microsoft sync")
            return 0
        
        print(f"Syncing events between {len(microsoft_connections)} Microsoft accounts...")
        
        # Group events by source account (extract email from provider_event_id or organizer)
        events_by_account = {}
        for event in microsoft_events:
            if not self._should_sync_microsoft_event(event):
                continue
            source_account = None
            if event.organizer:
                source_account = event.organizer
            elif event.provider_event_id:
                # Try to extract email from provider_event_id if it contains one
                source_account = event.provider_event_id
            
            if source_account:
                events_by_account.setdefault(source_account, []).append(event)
        
        print(f"Events grouped by account: {[(acc, len(evts)) for acc, evts in events_by_account.items()]}")
        
        for target_connection in microsoft_connections:
            target_email = target_connection.provider_account_email
            print(f"\nSyncing events TO account: {target_email}")
            
            # Get Microsoft Graph client for target connection
            user = User.query.get(target_connection.user_id)
            if not user:
                print(f"  User {target_connection.user_id} not found, skipping")
                continue
            
            try:
                client = self.microsoft_service.get_graph_client(user)
            except Exception as auth_error:
                print(f"  Unable to get Microsoft Graph client: {auth_error}")
                continue
            
            # Collect events from other accounts
            events_to_sync = []
            for source_account, events in events_by_account.items():
                if source_account != target_email:
                    events_to_sync.extend(events)
            
            if not events_to_sync:
                print(f"  No events to sync to {target_email}")
                continue
            
            print(f"  Preparing {len(events_to_sync)} events for {target_email}")
            
            for event in events_to_sync:
                try:
                    mapping = self._find_mapping(
                        user_id=user.id,
                        original_provider='microsoft',
                        original_provider_event_id=event.provider_event_id,
                        mirror_provider='microsoft',
                        mirror_account_email=target_email
                    )
                    
                    blocker_payload = self._build_microsoft_blocker_payload(event)
                    
                    if mapping:
                        # Update existing blocker
                        updated = client.update_calendar_event(mapping.mirror_provider_event_id, blocker_payload)
                        if updated:
                            self._update_local_blocker(mapping, event)
                            synced_count += 1
                        continue
                    
                    # Create new blocker
                    response = client.create_calendar_event(blocker_payload)
                    if response:
                        mirror_event = self._create_local_blocker_event(
                            user_id=user.id,
                            provider='microsoft',
                            provider_event_id=response.get('id', f"mirror_ms_{event.id}"),
                            start_time=event.start_time,
                            end_time=event.end_time,
                            all_day=event.all_day,
                            calendar_id='default'
                        )
                        
                        mapping = EventMirrorMapping(
                            user_id=user.id,
                            original_provider='microsoft',
                            original_event_id=event.id,
                            original_provider_event_id=event.provider_event_id or f"microsoft_local_{event.id}",
                            mirror_provider='microsoft',
                            mirror_event_id=mirror_event.id,
                            mirror_provider_event_id=mirror_event.provider_event_id
                        )
                        db.session.add(mapping)
                        synced_count += 1
                        print(f"    ✅ Created blocker '{self.MIRROR_TITLE}' in {target_email}")
                
                except Exception as e:
                    print(f"    ❌ Error syncing event '{event.title}' to {target_email}: {e}")
                    continue
        
        db.session.commit()
        return synced_count
    
    def _format_datetime(self, dt: datetime) -> str:
        """Ensure datetimes are serialized with IST timezone information."""
        if not dt:
            return datetime.utcnow().isoformat()
        if dt.tzinfo:
            return dt.isoformat()
        return self.ist_tz.localize(dt).isoformat()
