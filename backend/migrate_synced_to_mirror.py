#!/usr/bin/env python3
"""
Utility script to migrate legacy [SYNCED] events into the new [Mirror] Busy blockers.

This script:
  - Updates existing database records so they follow the new blocker format
  - Attempts to update the remote Google/Microsoft events without sending notifications
  - Creates EventMirrorMapping rows to track the relationship between originals and blockers

Run from the backend directory:
    python migrate_synced_to_mirror.py
"""

from datetime import datetime
from sqlalchemy import or_

from app import create_app
from models.event_model import Event, db
from models.user_model import User
from models.calendar_connection_model import CalendarConnection
from models.event_mirror_mapping_model import EventMirrorMapping
from services.google_service import GoogleCalendarService
from services.microsoft_service import MicrosoftCalendarService

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
except ImportError:
    Credentials = None
    Request = None
    build = None

MIRROR_TITLE = '[Mirror] Busy'
IST_TIMEZONE = 'Asia/Kolkata'


def extract_remote_id(provider_event_id):
    if not provider_event_id:
        return None, None
    if ':' in provider_event_id:
        account_email, remote_id = provider_event_id.split(':', 1)
        return account_email, remote_id
    return None, provider_event_id


def build_google_payload(event):
    return {
        'summary': MIRROR_TITLE,
        'start': {
            'dateTime': event.start_time.isoformat(),
            'timeZone': IST_TIMEZONE
        },
        'end': {
            'dateTime': event.end_time.isoformat(),
            'timeZone': IST_TIMEZONE
        },
        'visibility': 'private',
        'transparency': 'opaque',
        'attendees': [],
        'reminders': {'useDefault': False},
        'guestsCanModify': False,
        'guestsCanInviteOthers': False,
        'guestsCanSeeOtherGuests': False
    }


def build_microsoft_payload(event):
    return {
        'subject': MIRROR_TITLE,
        'start': {
            'dateTime': event.start_time.isoformat(),
            'timeZone': IST_TIMEZONE
        },
        'end': {
            'dateTime': event.end_time.isoformat(),
            'timeZone': IST_TIMEZONE
        },
        'sensitivity': 'private',
        'showAs': 'busy',
        'isReminderOn': False,
        'attendees': [],
        'isOnlineMeeting': False,
        'allowNewTimeProposals': False
    }


def update_google_event(google_service, event):
    user = User.query.get(event.user_id)
    if not user:
        return False
    account_email, remote_event_id = extract_remote_id(event.provider_event_id)
    calendar_id = 'primary'
    
    if account_email:
        connection = CalendarConnection.query.filter_by(
            provider='google',
            provider_account_email=account_email,
            user_id=user.id
        ).first()
        if not connection or not Credentials or not build:
            return False
        token_info = connection.get_token()
        if not token_info:
            return False
        credentials = Credentials(
            token=token_info['token'],
            refresh_token=token_info.get('refresh_token'),
            token_uri=token_info.get('token_uri', 'https://oauth2.googleapis.com/token'),
            client_id=token_info.get('client_id', google_service.client_id),
            client_secret=token_info.get('client_secret', google_service.client_secret),
            scopes=token_info.get('scopes', google_service.SCOPES)
        )
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            token_info['token'] = credentials.token
            connection.set_token(token_info)
            db.session.commit()
        service = build('calendar', 'v3', credentials=credentials)
        calendar_id = connection.calendar_id or 'primary'
        try:
            service.events().patch(
                calendarId=calendar_id,
                eventId=remote_event_id,
                body=build_google_payload(event),
                sendUpdates='none',
                conferenceDataVersion=0
            ).execute()
            return True
        except Exception as exc:
            print(f"      ⚠️ Unable to patch Google event for {account_email}: {exc}")
            return False
    else:
        client = google_service.get_calendar_client(user)
        response = client.update_calendar_event(remote_event_id, build_google_payload(event), calendar_id=calendar_id)
        return bool(response)


def update_microsoft_event(microsoft_service, event):
    user = User.query.get(event.user_id)
    if not user:
        return False
    client = microsoft_service.get_graph_client(user)
    response = client.update_calendar_event(event.provider_event_id, build_microsoft_payload(event))
    return bool(response)


def create_mapping(original_event, mirror_event, mirror_provider_event_id):
    if not original_event or not mirror_event or not mirror_provider_event_id:
        return
    existing = EventMirrorMapping.query.filter_by(
        user_id=mirror_event.user_id,
        original_provider=original_event.provider,
        original_provider_event_id=original_event.provider_event_id,
        mirror_provider=mirror_event.provider
    ).first()
    if existing:
        return
    mapping = EventMirrorMapping(
        user_id=mirror_event.user_id,
        original_provider=original_event.provider,
        original_event_id=original_event.id,
        original_provider_event_id=original_event.provider_event_id,
        mirror_provider=mirror_event.provider,
        mirror_event_id=mirror_event.id,
        mirror_provider_event_id=mirror_provider_event_id
    )
    db.session.add(mapping)


def find_original_event(mirror_event):
    normalized_title = mirror_event.title.replace('[SYNCED]', '').strip()
    if not normalized_title:
        return None
    query = Event.query.filter(
        Event.id != mirror_event.id,
        Event.start_time == mirror_event.start_time,
        Event.provider != mirror_event.provider,
        or_(
            Event.title == normalized_title,
            Event.title == f"[Mirror] {normalized_title}",
            Event.title == MIRROR_TITLE
        )
    )
    return query.first()


def migrate_synced_events():
    app = create_app()
    with app.app_context():
        google_service = GoogleCalendarService()
        microsoft_service = None
        
        synced_events = Event.query.filter(Event.title.like('[SYNCED]%')).all()
        if not synced_events:
            print("No [SYNCED] events found. Nothing to migrate.")
            return
        
        print(f"Found {len(synced_events)} legacy synced events. Migrating...")
        migrated = 0
        
        for event in synced_events:
            print(f"\nProcessing event #{event.id}: {event.title} ({event.provider})")
            remote_updated = False
            
            if event.provider == 'google':
                remote_updated = update_google_event(google_service, event)
            elif event.provider == 'microsoft':
                if microsoft_service is None:
                    microsoft_service = MicrosoftCalendarService()
                remote_updated = update_microsoft_event(microsoft_service, event)
            
            if remote_updated:
                print("  ✅ Remote calendar updated without notifications.")
            else:
                print("  ⚠️ Unable to update remote calendar (will still update database).")
            
            event.title = MIRROR_TITLE
            event.description = ''
            event.location = ''
            event.set_attendees([])
            if not event.organizer and event.user:
                event.organizer = event.user.email
            event.last_synced = datetime.utcnow()
            
            _, remote_id = extract_remote_id(event.provider_event_id)
            original_event = find_original_event(event)
            create_mapping(original_event, event, remote_id or event.provider_event_id)
            migrated += 1
        
        db.session.commit()
        print(f"\nMigration complete. Updated {migrated} events to the new [Mirror] format.")


if __name__ == '__main__':
    migrate_synced_events()

