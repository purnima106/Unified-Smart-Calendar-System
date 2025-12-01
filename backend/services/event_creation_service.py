#!/usr/bin/env python3
"""
Event Creation Service
Creates NEW events and sends notifications to participants
"""

import pytz
from datetime import datetime, timedelta
from models.user_model import User, db
from models.event_model import Event
from services.google_service import GoogleCalendarService
from services.microsoft_service import MicrosoftCalendarService

class EventCreationService:
    """Service to create NEW events and send notifications to participants"""
    
    def __init__(self):
        self.google_service = GoogleCalendarService()
        self.microsoft_service = MicrosoftCalendarService()
        self.ist_tz = pytz.timezone('Asia/Kolkata')
    
    def create_new_event(self, event_data, target_calendar='both'):
        """Create a NEW event and send notifications to participants"""
        from flask import current_app
        microsoft_enabled = current_app.config.get('MICROSOFT_ENABLED', False)
        
        try:
            print("Creating NEW event with notifications to participants...")
            
            # Get all users with connected calendars (only Google if Microsoft is disabled)
            if microsoft_enabled:
                users = User.query.filter(
                    (User.google_calendar_connected == True) | 
                    (User.microsoft_calendar_connected == True)
                ).all()
            else:
                users = User.query.filter(
                    User.google_calendar_connected == True
                ).all()
            
            if not users:
                print("No users with connected calendars found")
                return {
                    'google_created': False,
                    'microsoft_created': False,
                    'message': 'No connected calendars found'
                }
            
            google_created = False
            microsoft_created = False
            
            # Create event in Google Calendar
            if target_calendar in ['google', 'both']:
                google_users = [u for u in users if u.google_calendar_connected]
                if google_users:
                    try:
                        google_user = google_users[0]
                        google_created = self._create_google_event(google_user, event_data)
                        print(f"Created Google event: {google_created}")
                    except Exception as e:
                        print(f"Error creating Google event: {e}")
            
            # Create event in Microsoft Calendar (only if enabled)
            if microsoft_enabled and target_calendar in ['microsoft', 'both']:
                microsoft_users = [u for u in users if u.microsoft_calendar_connected]
                if microsoft_users:
                    try:
                        microsoft_user = microsoft_users[0]
                        microsoft_created = self._create_microsoft_event(microsoft_user, event_data)
                        print(f"Created Microsoft event: {microsoft_created}")
                    except Exception as e:
                        print(f"Error creating Microsoft event: {e}")
            elif target_calendar == 'microsoft':
                print("Microsoft Calendar integration is disabled. Event will not be created in Microsoft.")
            
            return {
                'google_created': google_created,
                'microsoft_created': microsoft_created,
                'message': f'NEW event created with notifications sent to participants'
            }
            
        except Exception as e:
            print(f"Event creation error: {e}")
            raise
    
    def _create_google_event(self, user, event_data):
        """Create NEW event in Google Calendar with notifications"""
        try:
            # Prepare event data for Google
            google_event_data = {
                'summary': event_data.get('title', 'New Event'),
                'description': event_data.get('description', ''),
                'location': event_data.get('location', ''),
                'start': {
                    'dateTime': event_data.get('start_time').isoformat(),
                    'timeZone': 'Asia/Kolkata'
                },
                'end': {
                    'dateTime': event_data.get('end_time').isoformat(),
                    'timeZone': 'Asia/Kolkata'
                },
                'guestsCanModify': False,
                'guestsCanInviteOthers': False,
                'guestsCanSeeOtherGuests': True
            }
            
            # Add attendees with notifications
            attendees = event_data.get('attendees', [])
            if attendees:
                google_event_data['attendees'] = [
                    {
                        'email': attendee.get('email', ''),
                        'displayName': attendee.get('name', ''),
                        'responseStatus': 'needsAction'  # This will send notifications
                    }
                    for attendee in attendees
                ]
                print(f"Adding {len(attendees)} attendees with notifications for NEW Google event")
            
            # Create the event using Google Calendar API
            client = self.google_service.get_calendar_client(user)
            response = client.create_calendar_event(google_event_data)
            
            if response:
                # Store the event in our database
                new_event = Event(
                    user_id=user.id,
                    title=event_data.get('title'),
                    description=event_data.get('description', ''),
                    location=event_data.get('location', ''),
                    start_time=event_data.get('start_time'),
                    end_time=event_data.get('end_time'),
                    all_day=event_data.get('all_day', False),
                    provider='google',
                    provider_event_id=response.get('id'),
                    calendar_id='primary',
                    organizer=user.email,
                    last_synced=datetime.utcnow()
                )
                
                # Set attendees
                if attendees:
                    new_event.set_attendees(attendees)
                
                db.session.add(new_event)
                db.session.commit()
                
                print(f"Created NEW Google event: {event_data.get('title')} with notifications")
                return True
            
            return False
            
        except Exception as e:
            print(f"Error creating Google event: {e}")
            return False
    
    def _create_microsoft_event(self, user, event_data):
        """Create NEW event in Microsoft Calendar with notifications"""
        try:
            # Prepare event data for Microsoft
            microsoft_event_data = {
                'subject': event_data.get('title', 'New Event'),
                'body': {
                    'content': event_data.get('description', ''),
                    'contentType': 'text'
                },
                'start': {
                    'dateTime': event_data.get('start_time').isoformat(),
                    'timeZone': 'Asia/Kolkata'
                },
                'end': {
                    'dateTime': event_data.get('end_time').isoformat(),
                    'timeZone': 'Asia/Kolkata'
                },
                'location': {
                    'displayName': event_data.get('location', '')
                },
                'isAllDay': event_data.get('all_day', False),
                'isOnlineMeeting': False,
                'allowNewTimeProposals': False
            }
            
            # Add attendees with notifications
            attendees = event_data.get('attendees', [])
            if attendees:
                microsoft_event_data['attendees'] = [
                    {
                        'emailAddress': {
                            'address': attendee.get('email', ''),
                            'name': attendee.get('name', '')
                        },
                        'type': 'required'  # This will send notifications
                    }
                    for attendee in attendees
                ]
                print(f"Adding {len(attendees)} attendees with notifications for NEW Microsoft event")
            
            # Create the event using Microsoft Graph API
            client = self.microsoft_service.get_graph_client(user)
            response = client.create_calendar_event(microsoft_event_data)
            
            if response:
                # Store the event in our database
                new_event = Event(
                    user_id=user.id,
                    title=event_data.get('title'),
                    description=event_data.get('description', ''),
                    location=event_data.get('location', ''),
                    start_time=event_data.get('start_time'),
                    end_time=event_data.get('end_time'),
                    all_day=event_data.get('all_day', False),
                    provider='microsoft',
                    provider_event_id=response.get('id'),
                    calendar_id='default',
                    organizer=user.email,
                    last_synced=datetime.utcnow()
                )
                
                # Set attendees
                if attendees:
                    new_event.set_attendees(attendees)
                
                db.session.add(new_event)
                db.session.commit()
                
                print(f"Created NEW Microsoft event: {event_data.get('title')} with notifications")
                return True
            
            return False
            
        except Exception as e:
            print(f"Error creating Microsoft event: {e}")
            return False
