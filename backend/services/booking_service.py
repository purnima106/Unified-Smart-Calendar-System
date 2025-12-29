from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

import requests
import uuid
import pytz

from sqlalchemy import text, select
from flask import current_app

from models.user_model import db, User
from models.booking_model import Booking
from models.availability_model import Availability
from models.calendar_connection_model import CalendarConnection
from models.event_model import Event
from services.notification_service import NotificationService


def _parse_iso(dt_str: str) -> datetime:
    """
    Parse ISO datetime string and convert to local naive datetime.
    Handles UTC times (ending in Z) by converting to local timezone (IST).
    """
    import pytz
    
    # Parse with timezone awareness
    if dt_str.endswith("Z"):
        # UTC time - parse as UTC
        dt_utc = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        # Convert to IST (Asia/Kolkata)
        ist_tz = pytz.timezone('Asia/Kolkata')
        dt_ist = dt_utc.astimezone(ist_tz)
        # Return as naive datetime in IST
        return dt_ist.replace(tzinfo=None)
    elif "+" in dt_str or (dt_str.count("-") > 2 and dt_str[-6] in "+-"):
        # Has timezone offset - parse and convert to IST
        dt_tz = datetime.fromisoformat(dt_str)
        ist_tz = pytz.timezone('Asia/Kolkata')
        dt_ist = dt_tz.astimezone(ist_tz)
        return dt_ist.replace(tzinfo=None)
    else:
        # No timezone info - assume it's already in local time (IST)
        return datetime.fromisoformat(dt_str)


def _overlaps(a_start: datetime, a_end: datetime, b_start: datetime, b_end: datetime) -> bool:
    return a_start < b_end and b_start < a_end


def _validate_duration(start: datetime, end: datetime, duration_minutes: int):
    if duration_minutes not in (30, 60):
        raise ValueError("duration_minutes must be 30 or 60")
    if end <= start:
        raise ValueError("end_time must be after start_time")
    actual = int((end - start).total_seconds() // 60)
    if actual != duration_minutes:
        raise ValueError("start_time/end_time do not match duration_minutes")
    # Enforce 30-minute grid starts to keep overlap checks consistent
    if start.minute % 30 != 0 or start.second != 0 or start.microsecond != 0:
        raise ValueError("Bookings must start on a 30-minute boundary")


def _pick_owner_connection(owner_id: int, preferred_provider: Optional[str] = None) -> Tuple[str, CalendarConnection]:
    """
    Decide which provider/calendar to create booking event into.
    Preference: honor preferred_provider if available, else fall back to Google then Microsoft.
    """
    provider_order = []
    if preferred_provider in ("google", "microsoft"):
        provider_order.append(preferred_provider)
        provider_order.append("microsoft" if preferred_provider == "google" else "google")
    else:
        provider_order = ["google", "microsoft"]

    for provider in provider_order:
        conn = CalendarConnection.query.filter_by(
            user_id=owner_id, provider=provider, is_active=True, is_connected=True
        ).order_by(CalendarConnection.created_at.asc()).first()
        if conn:
            return provider, conn

    raise ValueError("Owner has no connected calendar to create booking event")


def _refresh_google_token(connection: CalendarConnection) -> str:
    """Refresh Google token if expired and return valid access token."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    
    token_info = connection.get_token()
    if not token_info:
        raise Exception(f"No token found for Google connection {connection.provider_account_email}")
    
    client_id = current_app.config.get('GOOGLE_CLIENT_ID')
    client_secret = current_app.config.get('GOOGLE_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        raise Exception("Google OAuth credentials not configured")
    
    credentials = Credentials(
        token=token_info.get('token'),
        refresh_token=token_info.get('refresh_token'),
        token_uri=token_info.get('token_uri', 'https://oauth2.googleapis.com/token'),
        client_id=token_info.get('client_id', client_id),
        client_secret=token_info.get('client_secret', client_secret),
        scopes=token_info.get('scopes', [
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/calendar.events'
        ])
    )
    
    # Check if token is expired or about to expire (within 5 minutes)
    expires_at = token_info.get('expires_at', 0)
    is_expired = expires_at > 0 and datetime.utcnow().timestamp() >= (expires_at - 300)  # 5 min buffer
    needs_refresh = credentials.expired or is_expired
    
    # Refresh if expired or about to expire
    if needs_refresh and credentials.refresh_token:
        try:
            print(f"Refreshing Google token for {connection.provider_account_email}...")
            credentials.refresh(Request())
            # Update stored token
            token_info.update({
                'token': credentials.token,
                'refresh_token': credentials.refresh_token or token_info.get('refresh_token'),
                'expires_at': credentials.expiry.timestamp() if credentials.expiry else (datetime.utcnow().timestamp() + 3600),
            })
            connection.set_token(token_info)
            db.session.commit()
            print(f"Google token refreshed successfully for {connection.provider_account_email}")
        except Exception as e:
            print(f"Error refreshing Google token for {connection.provider_account_email}: {e}")
            import traceback
            traceback.print_exc()
            # If refresh fails, try using the existing token anyway (might still be valid)
            if not credentials.token:
                raise Exception(f"Failed to refresh Google token and no valid token available: {str(e)}")
    
    if not credentials.token:
        raise Exception(f"No valid access token available for Google connection {connection.provider_account_email}")
    
    return credentials.token


def _refresh_microsoft_token(connection: CalendarConnection) -> str:
    """Refresh Microsoft token if expired and return valid access token."""
    import msal
    
    token_info = connection.get_token()
    if not token_info:
        raise Exception(f"No token found for Microsoft connection {connection.provider_account_email}")
    
    client_id = current_app.config.get('MICROSOFT_CLIENT_ID')
    client_secret = current_app.config.get('MICROSOFT_CLIENT_SECRET')
    tenant_id = current_app.config.get('MICROSOFT_TENANT_ID', 'common')
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    
    # Check if token is expired
    if datetime.utcnow().timestamp() > token_info.get('expires_at', 0):
        app = msal.ConfidentialClientApplication(
            client_id,
            authority=authority,
            client_credential=client_secret
        )
        
        result = app.acquire_token_by_refresh_token(
            token_info.get('refresh_token'),
            scopes=['Calendars.ReadWrite', 'User.Read']
        )
        
        if "error" in result:
            raise Exception(f"Microsoft token refresh failed: {result.get('error_description', 'Unknown error')}")
        
        # Update stored token
        token_info.update({
            'access_token': result['access_token'],
            'refresh_token': result.get('refresh_token', token_info.get('refresh_token')),
            'expires_in': result.get('expires_in', 3600),
            'expires_at': datetime.utcnow().timestamp() + result.get('expires_in', 3600)
        })
        connection.set_token(token_info)
        db.session.commit()
    
    return token_info.get('access_token')


def _create_google_meeting(token: str, calendar_id: str, title: str, description: str, start: datetime, end: datetime, connection: CalendarConnection = None) -> Tuple[Optional[str], Optional[str]]:
    """
    Create Google Calendar event with meeting link.
    If connection is provided and we get a 401, will attempt to refresh token and retry once.
    """
    url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
    params = {
        "sendUpdates": "none",
        "conferenceDataVersion": 1,
    }
    body = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start.isoformat() + "Z", "timeZone": "UTC"},
        "end": {"dateTime": end.isoformat() + "Z", "timeZone": "UTC"},
        "visibility": "private",
        "guestsCanModify": False,
        "guestsCanInviteOthers": False,
        "guestsCanSeeOtherGuests": False,
        "conferenceData": {
            "createRequest": {
                "requestId": str(uuid.uuid4()),
                "conferenceSolutionKey": {"type": "hangoutsMeet"},
            }
        },
    }

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, params=params, json=body, timeout=30)
    
    # If we get 401 and have a connection, try refreshing token once
    if resp.status_code == 401 and connection:
        print(f"Got 401 error, attempting to refresh token and retry...")
        try:
            new_token = _refresh_google_token(connection)
            headers = {"Authorization": f"Bearer {new_token}", "Content-Type": "application/json"}
            resp = requests.post(url, headers=headers, params=params, json=body, timeout=30)
        except Exception as refresh_error:
            print(f"Token refresh failed during retry: {refresh_error}")
            raise Exception(f"Google event creation failed: 401 Unauthenticated. Please reconnect your Google account in the dashboard.")
    
    if not resp.ok:
        error_msg = resp.text
        if resp.status_code == 401:
            error_msg = "401 Unauthenticated. Your Google account token has expired or been revoked. Please reconnect your Google account in the dashboard."
        raise Exception(f"Google event creation failed: {resp.status_code} {error_msg}")
    
    data = resp.json()
    event_id = data.get("id")
    meet_link = data.get("hangoutLink")
    # Some responses include conferenceData.entryPoints
    if not meet_link:
        conf = data.get("conferenceData") or {}
        for ep in conf.get("entryPoints", []) or []:
            if ep.get("entryPointType") == "video" and ep.get("uri"):
                meet_link = ep.get("uri")
                break
    return event_id, meet_link


def _create_microsoft_meeting(access_token: str, title: str, description: str, start: datetime, end: datetime) -> Tuple[Optional[str], Optional[str]]:
    url = "https://graph.microsoft.com/v1.0/me/events"
    body = {
        "subject": title,
        "body": {"contentType": "HTML", "content": description.replace("\n", "<br/>")},
        "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
        "isOnlineMeeting": True,
        "onlineMeetingProvider": "teamsForBusiness",
        "sensitivity": "private",
        "showAs": "busy",
    }
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=body, timeout=30)
    if not resp.ok:
        raise Exception(f"Microsoft event creation failed: {resp.status_code} {resp.text}")
    data = resp.json()
    event_id = data.get("id")
    meeting_link = (data.get("onlineMeeting") or {}).get("joinUrl")
    return event_id, meeting_link


def _create_google_event_without_meeting(token: str, calendar_id: str, title: str, description: str, start: datetime, end: datetime, connection: CalendarConnection = None) -> Optional[str]:
    """Create Google Calendar event without conference data (for manual meeting links).
    If connection is provided and we get a 401, will attempt to refresh token and retry once.
    """
    url = f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
    params = {
        "sendUpdates": "none",
    }
    body = {
        "summary": title,
        "description": description,
        "start": {"dateTime": start.isoformat() + "Z", "timeZone": "UTC"},
        "end": {"dateTime": end.isoformat() + "Z", "timeZone": "UTC"},
        "visibility": "private",
        "guestsCanModify": False,
        "guestsCanInviteOthers": False,
        "guestsCanSeeOtherGuests": False,
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, params=params, json=body, timeout=30)
    
    # If we get 401 and have a connection, try refreshing token once
    if resp.status_code == 401 and connection:
        print(f"Got 401 error, attempting to refresh token and retry...")
        try:
            new_token = _refresh_google_token(connection)
            headers = {"Authorization": f"Bearer {new_token}", "Content-Type": "application/json"}
            resp = requests.post(url, headers=headers, params=params, json=body, timeout=30)
        except Exception as refresh_error:
            print(f"Token refresh failed during retry: {refresh_error}")
            raise Exception(f"Google event creation failed: 401 Unauthenticated. Please reconnect your Google account in the dashboard.")
    
    if not resp.ok:
        error_msg = resp.text
        if resp.status_code == 401:
            error_msg = "401 Unauthenticated. Your Google account token has expired or been revoked. Please reconnect your Google account in the dashboard."
        raise Exception(f"Google event creation failed: {resp.status_code} {error_msg}")
    data = resp.json()
    return data.get("id")


def _create_microsoft_event_without_meeting(access_token: str, title: str, description: str, start: datetime, end: datetime) -> Optional[str]:
    """Create Microsoft Calendar event without online meeting (for manual meeting links)."""
    url = "https://graph.microsoft.com/v1.0/me/events"
    body = {
        "subject": title,
        "body": {"contentType": "HTML", "content": description},
        "start": {"dateTime": start.isoformat(), "timeZone": "UTC"},
        "end": {"dateTime": end.isoformat(), "timeZone": "UTC"},
        "isOnlineMeeting": False,
        "sensitivity": "private",
        "showAs": "busy",
    }
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    resp = requests.post(url, headers=headers, json=body, timeout=30)
    if not resp.ok:
        raise Exception(f"Microsoft event creation failed: {resp.status_code} {resp.text}")
    data = resp.json()
    return data.get("id")


class BookingService:
    """
    Create a booking safely:
    - validate availability window
    - re-check busy using DB (events + bookings)
    - lock owner row to prevent race conditions (Postgres) before final insert
    - create event in owner's provider calendar
    - store booking record
    - send notifications (best-effort)
    """

    @staticmethod
    def create_public_booking(payload: Dict[str, Any]) -> Dict[str, Any]:
        username = (payload.get("username") or "").strip()
        if not username:
            raise ValueError("username is required")

        client_name = (payload.get("client_name") or "").strip()
        client_email = (payload.get("client_email") or "").strip()
        client_note = (payload.get("client_note") or "").strip()
        if not client_name:
            raise ValueError("client_name is required")
        if "@" not in client_email:
            raise ValueError("client_email is invalid")

        preferred_provider = (payload.get("meeting_provider") or payload.get("preferred_provider") or "").strip().lower()
        if preferred_provider and preferred_provider not in ("google", "microsoft"):
            raise ValueError("meeting_provider must be either 'google' or 'microsoft'")

        duration_minutes = int(payload.get("duration_minutes", 30))
        start = _parse_iso(payload.get("start_time"))
        end = _parse_iso(payload.get("end_time"))
        
        # #region agent log
        try:
            import os
            # project root/.cursor/debug.log
            log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.cursor', 'debug.log')
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, 'a', encoding='utf-8') as f:
                import json
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"booking_service.py:273","message":"Raw payload times received","data":{"start_time_raw":payload.get("start_time"),"end_time_raw":payload.get("end_time"),"username":username},"timestamp":int(datetime.utcnow().timestamp()*1000)}) + '\n')
        except Exception as e:
            print(f"DEBUG LOG ERROR: {e}")
        # #endregion
        
        # Normalize times (remove microseconds, round to seconds)
        start = start.replace(microsecond=0)
        end = end.replace(microsecond=0)
        
        # #region agent log
        try:
            import os
            log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.cursor', 'debug.log')
            with open(log_path, 'a', encoding='utf-8') as f:
                import json
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"A","location":"booking_service.py:280","message":"Normalized slot times","data":{"start":start.isoformat(),"end":end.isoformat(),"start_date":str(start.date()),"start_time_only":str(start.time()),"end_time_only":str(end.time())},"timestamp":int(datetime.utcnow().timestamp()*1000)}) + '\n')
        except Exception as e:
            print(f"DEBUG LOG ERROR: {e}")
        # #endregion
        
        _validate_duration(start, end, duration_minutes)

        owner = User.query.filter(User.public_username == username).first()
        if not owner:
            raise ValueError("Owner not found")

        # #region agent log
        try:
            import os
            log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.cursor', 'debug.log')
            with open(log_path, 'a', encoding='utf-8') as f:
                import json
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"booking_service.py:288","message":"Owner lookup result","data":{"owner_id":owner.id,"owner_email":owner.email,"public_username":owner.public_username},"timestamp":int(datetime.utcnow().timestamp()*1000)}) + '\n')
        except Exception as e:
            print(f"DEBUG LOG ERROR: {e}")
        # #endregion

        # Check requested slot is within availability for that weekday
        dow = start.weekday()  # 0=Mon
        
        # #region agent log
        try:
            import os
            log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.cursor', 'debug.log')
            with open(log_path, 'a', encoding='utf-8') as f:
                import json
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"booking_service.py:295","message":"Day of week calculation","data":{"dow":dow,"dow_name":["Mon","Tue","Wed","Thu","Fri","Sat","Sun"][dow],"start_date":str(start.date())},"timestamp":int(datetime.utcnow().timestamp()*1000)}) + '\n')
        except Exception as e:
            print(f"DEBUG LOG ERROR: {e}")
        # #endregion
        
        rule = Availability.query.filter_by(owner_id=owner.id, day_of_week=dow).first()
        
        # #region agent log
        try:
            import os
            log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.cursor', 'debug.log')
            with open(log_path, 'a', encoding='utf-8') as f:
                import json
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"B","location":"booking_service.py:299","message":"Availability rule lookup","data":{"rule_found":rule is not None,"owner_id":owner.id,"day_of_week":dow,"rule_id":rule.id if rule else None,"rule_start_time":str(rule.start_time) if rule else None,"rule_end_time":str(rule.end_time) if rule else None},"timestamp":int(datetime.utcnow().timestamp()*1000)}) + '\n')
        except Exception as e:
            print(f"DEBUG LOG ERROR: {e}")
        # #endregion
        
        if not rule:
            print(f"No availability rule found for day_of_week={dow}, owner_id={owner.id}")
            raise ValueError("Slot not within owner's availability")
        
        window_start = datetime.combine(start.date(), rule.start_time)
        window_end = datetime.combine(start.date(), rule.end_time)
        
        # Normalize window times (remove microseconds)
        window_start = window_start.replace(microsecond=0)
        window_end = window_end.replace(microsecond=0)
        
        # #region agent log
        try:
            import os
            log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.cursor', 'debug.log')
            with open(log_path, 'a', encoding='utf-8') as f:
                import json
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"booking_service.py:310","message":"Window calculation","data":{"window_start":window_start.isoformat(),"window_end":window_end.isoformat(),"rule_start_time":str(rule.start_time),"rule_end_time":str(rule.end_time),"start_date":str(start.date())},"timestamp":int(datetime.utcnow().timestamp()*1000)}) + '\n')
        except Exception as e:
            print(f"DEBUG LOG ERROR: {e}")
        # #endregion
        
        # IMPORTANT: Match the slot generation logic exactly
        # Slots are generated with: day_end = min(window_end, end_dt) and t + slot_len <= day_end
        # So slots can end exactly at day_end, which might be less than or equal to window_end
        # We need to allow slots that are within the window with some tolerance for rounding
        # Use a larger epsilon (30 seconds) to account for:
        # - Rounding differences from frontend time normalization
        # - Timezone conversion issues
        # - The fact that day_end might be slightly different from window_end
        epsilon = timedelta(seconds=30)
        
        # #region agent log
        try:
            import os
            log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.cursor', 'debug.log')
            with open(log_path, 'a', encoding='utf-8') as f:
                import json
                start_check = start < window_start - epsilon
                end_check = end > window_end + epsilon
                f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"C","location":"booking_service.py:318","message":"Availability comparison","data":{"slot_start":start.isoformat(),"slot_end":end.isoformat(),"window_start":window_start.isoformat(),"window_end":window_end.isoformat(),"epsilon_seconds":30,"start_too_early":start_check,"end_too_late":end_check,"start_diff_seconds":(start - (window_start - epsilon)).total_seconds() if not start_check else None,"end_diff_seconds":((window_end + epsilon) - end).total_seconds() if not end_check else None},"timestamp":int(datetime.utcnow().timestamp()*1000)}) + '\n')
        except Exception as e:
            print(f"DEBUG LOG ERROR: {e}")
        # #endregion
        
        print(f"\n{'='*80}")
        print(f"AVAILABILITY VALIDATION DEBUG")
        print(f"{'='*80}")
        print(f"Slot being booked:")
        print(f"  start: {start} ({start.isoformat()})")
        print(f"  end:   {end} ({end.isoformat()})")
        print(f"  date:  {start.date()}")
        print(f"  day_of_week: {dow} ({['Mon','Tue','Wed','Thu','Fri','Sat','Sun'][dow]})")
        print(f"\nAvailability rule found:")
        print(f"  rule.start_time: {rule.start_time} (type: {type(rule.start_time)})")
        print(f"  rule.end_time:   {rule.end_time} (type: {type(rule.end_time)})")
        print(f"\nWindow calculation:")
        print(f"  window_start: {window_start} ({window_start.isoformat()})")
        print(f"  window_end:   {window_end} ({window_end.isoformat()})")
        print(f"\nComparison (epsilon={epsilon.total_seconds()}s):")
        start_diff = (start - (window_start - epsilon)).total_seconds()
        end_diff = ((window_end + epsilon) - end).total_seconds()
        print(f"  start check: {start} < {window_start - epsilon} = {start < window_start - epsilon} (diff: {start_diff}s)")
        print(f"  end check:   {end} > {window_end + epsilon} = {end > window_end + epsilon} (diff: {end_diff}s)")
        print(f"{'='*80}\n")
        
        if start < window_start - epsilon:
            diff_seconds = (window_start - start).total_seconds()
            diff_hours = diff_seconds / 3600
            print(f"❌ VALIDATION FAILED: Slot starts too early")
            print(f"   Slot start: {start} ({start.strftime('%I:%M %p') if hasattr(start, 'strftime') else start})")
            print(f"   Window start: {window_start} ({window_start.strftime('%I:%M %p') if hasattr(window_start, 'strftime') else window_start})")
            print(f"   Difference: {diff_seconds:.0f} seconds ({diff_hours:.2f} hours)")
            if abs(diff_hours - 12) < 1:  # If difference is ~12 hours, likely AM/PM confusion
                print(f"   ⚠️  WARNING: ~12 hour difference detected - possible AM/PM confusion!")
            raise ValueError(f"Slot not within owner's availability (starts {diff_hours:.1f}h too early)")
        if end > window_end + epsilon:
            diff_seconds = (end - window_end).total_seconds()
            diff_hours = diff_seconds / 3600
            print(f"❌ VALIDATION FAILED: Slot ends too late")
            print(f"   Slot end: {end} ({end.strftime('%I:%M %p') if hasattr(end, 'strftime') else end})")
            print(f"   Window end: {window_end} ({window_end.strftime('%I:%M %p') if hasattr(window_end, 'strftime') else window_end})")
            print(f"   Difference: {diff_seconds:.0f} seconds ({diff_hours:.2f} hours)")
            if abs(diff_hours - 12) < 1:  # If difference is ~12 hours, likely AM/PM confusion
                print(f"   ⚠️  WARNING: ~12 hour difference detected - possible AM/PM confusion!")
            raise ValueError(f"Slot not within owner's availability (ends {diff_hours:.1f}h too late)")

        # Lock owner row to serialize bookings per owner (prevents double booking races on Postgres).
        try:
            stmt = select(User).where(User.id == owner.id).with_for_update()
            db.session.execute(stmt).first()
        except Exception:
            # SQLite etc. may not support FOR UPDATE; continue with best-effort.
            pass

        # Re-check busy right before insert
        existing_bookings = Booking.query.filter(
            Booking.owner_id == owner.id,
            Booking.start_time < end,
            Booking.end_time > start,
        ).all()
        if any(_overlaps(start, end, b.start_time, b.end_time) for b in existing_bookings):
            raise ValueError("Slot no longer available")

        existing_events = Event.query.filter(
            Event.user_id == owner.id,
            Event.start_time < end,
            Event.end_time > start,
        ).all()
        if any(_overlaps(start, end, e.start_time, e.end_time) for e in existing_events):
            raise ValueError("Slot no longer available")

        provider, conn = _pick_owner_connection(owner.id, preferred_provider or None)

        title = f"Booking: {client_name}"
        description = f"Client: {client_name} ({client_email})\n\nNote: {client_note}".strip()

        calendar_event_id = None
        meeting_link = None
        
        # Check if manual meeting link is provided
        manual_meeting_link = payload.get("manual_meeting_link", "").strip()
        if manual_meeting_link:
            # Use manual link, but still try to create calendar event
            meeting_link = manual_meeting_link
            print(f"Using manual meeting link: {meeting_link}")
        
        # Try to create calendar event with meeting link
        try:
            if provider == "google":
                # Refresh token if needed before creating meeting
                try:
                    access_token = _refresh_google_token(conn)
                except Exception as token_error:
                    print(f"Token refresh error: {token_error}")
                    # If token refresh fails, try to get the token anyway (might still be valid)
                    token_info = conn.get_token()
                    if token_info and token_info.get('token'):
                        access_token = token_info.get('token')
                        print(f"Using existing token despite refresh error")
                    else:
                        raise Exception(f"Failed to get valid Google access token. Please reconnect your Google account: {str(token_error)}")
                
                if not manual_meeting_link:
                    # Only create meeting if manual link not provided
                    calendar_event_id, auto_meeting_link = _create_google_meeting(
                        token=access_token,
                        calendar_id=conn.calendar_id or "primary",
                        title=title,
                        description=description,
                        start=start,
                        end=end,
                        connection=conn,  # Pass connection for retry on 401
                    )
                    if auto_meeting_link:
                        meeting_link = auto_meeting_link
                else:
                    # Create event without conference data if manual link provided
                    calendar_event_id = _create_google_event_without_meeting(
                        token=access_token,
                        calendar_id=conn.calendar_id or "primary",
                        title=title,
                        description=f"{description}\n\nMeeting Link: {meeting_link}",
                        start=start,
                        end=end,
                        connection=conn,  # Pass connection for retry on 401
                    )
            else:
                # Refresh token if needed before creating meeting
                access_token = _refresh_microsoft_token(conn)
                if not manual_meeting_link:
                    # Only create meeting if manual link not provided
                    calendar_event_id, auto_meeting_link = _create_microsoft_meeting(
                        access_token=access_token,
                        title=title,
                        description=description,
                        start=start,
                        end=end,
                    )
                    if auto_meeting_link:
                        meeting_link = auto_meeting_link
                else:
                    # Create event without online meeting if manual link provided
                    calendar_event_id = _create_microsoft_event_without_meeting(
                        access_token=access_token,
                        title=title,
                        description=f"{description}<br/><br/>Meeting Link: <a href='{meeting_link}'>{meeting_link}</a>",
                        start=start,
                        end=end,
                    )
        except Exception as e:
            print(f"Error creating calendar event: {e}")
            import traceback
            traceback.print_exc()
            # If manual link provided, continue with booking even if event creation fails
            if not manual_meeting_link:
                raise Exception(f"Failed to create calendar event: {str(e)}")
            # Otherwise, allow booking to proceed with manual link

        booking = Booking(
            owner_id=owner.id,
            client_name=client_name,
            client_email=client_email,
            client_note=client_note or None,
            start_time=start,
            end_time=end,
            provider=provider,
            calendar_event_id=calendar_event_id,
            meeting_link=meeting_link,
        )
        db.session.add(booking)

        provider_event_identifier = None
        if calendar_event_id:
            provider_event_identifier = f"{conn.provider_account_email}:{calendar_event_id}"
        else:
            provider_event_identifier = f"{conn.provider_account_email}:manual-{uuid.uuid4().hex}"

        event_record = Event(
            user_id=owner.id,
            title=title,
            description=description,
            start_time=start,
            end_time=end,
            provider=provider,
            provider_event_id=provider_event_identifier,
            calendar_id=conn.calendar_id or 'primary',
            organizer=conn.provider_account_email,
            meet_link=meeting_link,
            color='#7c3aed',
            last_synced=datetime.utcnow(),
        )
        db.session.add(event_record)
        db.session.commit()

        # Best-effort notifications (do not fail booking if email fails)
        try:
            NotificationService.send_email(
                to_email=client_email,
                subject="Meeting booking confirmed",
                body=f"Your meeting is confirmed.\n\nWhen: {start.isoformat()} - {end.isoformat()}\nMeeting link: {meeting_link or 'TBD'}",
            )
            NotificationService.send_email(
                to_email=owner.email,
                subject="New booking received",
                body=f"New booking from {client_name} ({client_email}).\n\nWhen: {start.isoformat()} - {end.isoformat()}\nMeeting link: {meeting_link or 'TBD'}\n\nNote:\n{client_note or '-'}",
            )
        except Exception as e:
            print(f"Notification failure (ignored): {e}")

        return booking.to_public_confirmation()


