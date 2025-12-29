from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple

import requests
import uuid

from sqlalchemy import text, select

from models.user_model import db, User
from models.booking_model import Booking
from models.availability_model import Availability
from models.calendar_connection_model import CalendarConnection
from models.event_model import Event
from services.notification_service import NotificationService


def _parse_iso(dt_str: str) -> datetime:
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).replace(tzinfo=None)


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


def _pick_owner_connection(owner_id: int) -> Tuple[str, CalendarConnection]:
    """
    Decide which provider/calendar to create booking event into.
    Preference: Google first, then Microsoft.
    """
    google_conn = CalendarConnection.query.filter_by(
        user_id=owner_id, provider="google", is_active=True, is_connected=True
    ).order_by(CalendarConnection.created_at.asc()).first()
    if google_conn:
        return "google", google_conn

    ms_conn = CalendarConnection.query.filter_by(
        user_id=owner_id, provider="microsoft", is_active=True, is_connected=True
    ).order_by(CalendarConnection.created_at.asc()).first()
    if ms_conn:
        return "microsoft", ms_conn

    raise ValueError("Owner has no connected calendar to create booking event")


def _create_google_meeting(token: str, calendar_id: str, title: str, description: str, start: datetime, end: datetime) -> Tuple[Optional[str], Optional[str]]:
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
    if not resp.ok:
        raise Exception(f"Google event creation failed: {resp.status_code} {resp.text}")
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

        duration_minutes = int(payload.get("duration_minutes", 30))
        start = _parse_iso(payload.get("start_time"))
        end = _parse_iso(payload.get("end_time"))
        _validate_duration(start, end, duration_minutes)

        owner = User.query.filter(User.public_username == username).first()
        if not owner:
            raise ValueError("Owner not found")

        # Check requested slot is within availability for that weekday
        dow = start.weekday()  # 0=Mon
        rule = Availability.query.filter_by(owner_id=owner.id, day_of_week=dow).first()
        if not rule:
            raise ValueError("Slot not within owner's availability")
        window_start = datetime.combine(start.date(), rule.start_time)
        window_end = datetime.combine(start.date(), rule.end_time)
        if start < window_start or end > window_end:
            raise ValueError("Slot not within owner's availability")

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

        provider, conn = _pick_owner_connection(owner.id)
        token_info = conn.get_token() or {}

        title = f"Booking: {client_name}"
        description = f"Client: {client_name} ({client_email})\n\nNote: {client_note}".strip()

        calendar_event_id = None
        meeting_link = None
        if provider == "google":
            calendar_event_id, meeting_link = _create_google_meeting(
                token=token_info.get("token"),
                calendar_id=conn.calendar_id or "primary",
                title=title,
                description=description,
                start=start,
                end=end,
            )
        else:
            calendar_event_id, meeting_link = _create_microsoft_meeting(
                access_token=token_info.get("access_token"),
                title=title,
                description=description,
                start=start,
                end=end,
            )

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


