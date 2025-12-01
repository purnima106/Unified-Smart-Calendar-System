import re
from typing import Any, Dict, Optional
from models.event_model import Event


class MeetingDetectionService:
    """Utility helpers to detect real meetings and filter out noise calendars."""

    GOOGLE_HOLIDAY_CALENDARS = {
        'en.indian#holiday@group.v.calendar.google.com',
        'en.usa#holiday@group.v.calendar.google.com',
        'holidays@group.v.calendar.google.com',
    }
    GOOGLE_BIRTHDAY_CALENDAR = 'contacts@group.v.calendar.google.com'
    GOOGLE_REMINDER_PREFIXES = ('reminders', 'tasks')
    GOOGLE_IGNORED_CATEGORIES = {'holiday', 'festival'}

    GOOGLE_MEET_KEYWORDS = ('meet.google.com', 'google meet', 'gmeet')
    TEAMS_KEYWORDS = ('teams.microsoft.com', 'microsoft teams', 'teams meeting')

    GOOGLE_MEET_PATTERN = re.compile(r'https?://meet\.google\.com/[a-z0-9\-]+', re.IGNORECASE)
    TEAMS_PATTERN = re.compile(r'https?://teams\.microsoft\.com/[^\s]+', re.IGNORECASE)

    @classmethod
    def is_google_real_meeting(
        cls,
        event_data: Optional[Dict[str, Any]] = None,
        event: Optional[Event] = None,
        calendar_id: Optional[str] = None
    ) -> bool:
        """Return True if the Google event represents a real meeting."""
        calendar_id = calendar_id or cls._extract_calendar_id(event_data, event)

        if cls._should_ignore_google_calendar(calendar_id):
            return False

        if cls._has_ignored_category(event_data):
            return False

        all_day = cls._is_all_day(event_data, event)
        has_meeting_link = cls._has_google_meeting_link(event_data, event)

        if all_day and not has_meeting_link:
            return False

        if has_meeting_link:
            return True

        if cls._description_has_meeting_hint(event_data, event):
            return True

        if cls._location_has_meeting_hint(event_data, event):
            return True

        if cls._has_attendees_with_default_type(event_data):
            return True

        return False

    @classmethod
    def is_microsoft_real_meeting(
        cls,
        event_data: Optional[Dict[str, Any]] = None,
        event: Optional[Event] = None
    ) -> bool:
        """Return True if the Microsoft event represents a real meeting."""
        if cls._is_microsoft_holiday_or_birthday(event_data, event):
            return False

        all_day = cls._is_all_day(event_data, event)
        has_online_info = cls._has_microsoft_online_info(event_data)
        has_teams_hint = cls._description_has_teams_hint(event_data, event) or cls._location_has_teams_hint(event_data, event)
        has_attendees = cls._has_microsoft_attendees(event_data, event)
        
        # Check if event has a location (indicates it might be a meeting)
        has_location = False
        if event_data:
            location = event_data.get('location', {})
            if isinstance(location, dict):
                location_name = location.get('displayName', '')
            else:
                location_name = str(location) if location else ''
            has_location = bool(location_name and location_name.strip())
        elif event:
            has_location = bool(event.location and event.location.strip())

        # For all-day events, require additional meeting indicators to avoid clutter
        if all_day:
            return has_online_info or has_teams_hint or has_attendees or has_location

        # For timed events:
        #  - Require a subject/title (already checked below)
        #  - Accept by default, even if there is no online info/attendees/location
        #    because many real meetings are simple personal or in-person meetings.
        has_subject = False
        if event_data:
            subject = event_data.get('subject', '')
            has_subject = bool(subject and subject.strip() and subject.lower() not in ['no title', 'untitled'])
        elif event:
            has_subject = bool(event.title and event.title.strip() and event.title.lower() not in ['no title', 'untitled'])

        if not has_subject:
            return False

        # Timed events with a valid subject are treated as meetings.
        return True

    # -----------------------
    # Google helper methods
    # -----------------------
    @classmethod
    def _should_ignore_google_calendar(cls, calendar_id: Optional[str]) -> bool:
        if not calendar_id:
            return False
        calendar_id = calendar_id.lower()
        if calendar_id in cls.GOOGLE_HOLIDAY_CALENDARS:
            return True
        if calendar_id == cls.GOOGLE_BIRTHDAY_CALENDAR:
            return True
        return any(calendar_id.startswith(prefix) for prefix in cls.GOOGLE_REMINDER_PREFIXES)

    @classmethod
    def _has_ignored_category(cls, event_data: Optional[Dict[str, Any]]) -> bool:
        if not event_data:
            return False
        categories = event_data.get('eventType') or event_data.get('categories')
        if not categories:
            return False
        if isinstance(categories, str):
            categories = [categories]
        categories = {str(cat).lower() for cat in categories}
        return any(cat in cls.GOOGLE_IGNORED_CATEGORIES for cat in categories)

    @staticmethod
    def _extract_calendar_id(event_data: Optional[Dict[str, Any]], event: Optional[Event]) -> Optional[str]:
        if event_data:
            calendar_id = event_data.get('organizer', {}).get('email')
            if calendar_id:
                return calendar_id
        if event and event.calendar_id:
            return event.calendar_id
        return None

    @staticmethod
    def _is_all_day(event_data: Optional[Dict[str, Any]], event: Optional[Event]) -> bool:
        if event_data:
            start = event_data.get('start', {})
            if start.get('date'):
                return True
            if start.get('dateTime') and start.get('timeZone') == 'UTC' and start.get('dateTime').endswith('T00:00:00Z'):
                return True
        if event:
            return bool(event.all_day)
        return False

    @classmethod
    def _has_google_meeting_link(cls, event_data: Optional[Dict[str, Any]], event: Optional[Event]) -> bool:
        if event_data:
            if event_data.get('hangoutLink'):
                return True
            conference_data = event_data.get('conferenceData', {})
            entry_points = conference_data.get('entryPoints', [])
            for entry in entry_points:
                if entry.get('entryPointType') == 'video' and entry.get('uri'):
                    return True
        if event and event.meet_link:
            return True
        return False

    @classmethod
    def _description_has_meeting_hint(cls, event_data: Optional[Dict[str, Any]], event: Optional[Event]) -> bool:
        description = ''
        if event_data:
            description = event_data.get('description', '') or ''
        elif event:
            description = event.description or ''
        description = description.lower()
        if not description:
            return False
        if cls.GOOGLE_MEET_PATTERN.search(description):
            return True
        return any(keyword in description for keyword in cls.GOOGLE_MEET_KEYWORDS)

    @classmethod
    def _location_has_meeting_hint(cls, event_data: Optional[Dict[str, Any]], event: Optional[Event]) -> bool:
        location = ''
        if event_data:
            location = event_data.get('location', '') or ''
        elif event:
            location = event.location or ''
        location = location.lower()
        if not location:
            return False
        if 'meet' in location:
            return True
        return any(keyword in location for keyword in cls.GOOGLE_MEET_KEYWORDS)

    @staticmethod
    def _has_attendees_with_default_type(event_data: Optional[Dict[str, Any]]) -> bool:
        if not event_data:
            return False
        attendees = event_data.get('attendees', [])
        event_type = (event_data.get('eventType') or '').lower()
        return bool(attendees) and event_type in ('default', '')

    # -----------------------
    # Microsoft helper methods
    # -----------------------
    @classmethod
    def _is_microsoft_holiday_or_birthday(cls, event_data: Optional[Dict[str, Any]], event: Optional[Event]) -> bool:
        if event_data:
            show_as = (event_data.get('showAs') or '').lower()
            categories = [c.lower() for c in event_data.get('categories', []) or []]
            subject = (event_data.get('subject') or '').lower()
            if show_as == 'free' and event_data.get('isAllDay'):
                return True
            if any(cat in cls.GOOGLE_IGNORED_CATEGORIES for cat in categories):
                return True
            if 'birthday' in subject or 'holiday' in subject or 'festival' in subject:
                return True
        if event:
            title = (event.title or '').lower()
            if 'birthday' in title or 'holiday' in title or 'festival' in title:
                return True
        return False

    @classmethod
    def _has_microsoft_online_info(cls, event_data: Optional[Dict[str, Any]]) -> bool:
        if not event_data:
            return False
        if event_data.get('isOnlineMeeting'):
            return True
        online_meeting = event_data.get('onlineMeeting')
        if online_meeting and online_meeting.get('joinUrl'):
            return True
        return False

    @classmethod
    def _description_has_teams_hint(cls, event_data: Optional[Dict[str, Any]], event: Optional[Event]) -> bool:
        description = ''
        if event_data:
            body = event_data.get('body', {}) or {}
            description = body.get('content', '') or ''
        elif event:
            description = event.description or ''
        description = description.lower()
        if not description:
            return False
        if cls.TEAMS_PATTERN.search(description):
            return True
        return any(keyword in description for keyword in cls.TEAMS_KEYWORDS)

    @classmethod
    def _location_has_teams_hint(cls, event_data: Optional[Dict[str, Any]], event: Optional[Event]) -> bool:
        location = ''
        if event_data:
            location = (event_data.get('location', {}) or {}).get('displayName', '') or ''
        elif event:
            location = event.location or ''
        location = location.lower()
        if not location:
            return False
        if 'teams' in location or 'online' in location:
            return True
        return any(keyword in location for keyword in cls.TEAMS_KEYWORDS)
    
    @classmethod
    def _has_microsoft_attendees(cls, event_data: Optional[Dict[str, Any]], event: Optional[Event]) -> bool:
        """Check if Microsoft event has attendees (indicates it's a meeting)."""
        if event_data:
            attendees = event_data.get('attendees', [])
            # If there are any attendees at all, it's likely a meeting
            # (Even if the organizer is included, having attendees list means it was shared/invited)
            if isinstance(attendees, list) and len(attendees) > 0:
                # Check if there are any valid attendee emails
                # Don't filter out organizer - if attendees list exists, it's likely a meeting
                attendee_count = 0
                for attendee in attendees:
                    attendee_email = attendee.get('emailAddress', {}).get('address', '')
                    if attendee_email and attendee_email.strip():
                        attendee_count += 1
                
                # If there's at least one attendee (even if it's the organizer), consider it a meeting
                # This handles cases where Microsoft includes the organizer in attendees
                return attendee_count > 0
        
        if event:
            # Check event's attendees if stored
            event_attendees = event.get_attendees() if hasattr(event, 'get_attendees') else []
            if isinstance(event_attendees, list) and len(event_attendees) > 0:
                return True
        
        return False

