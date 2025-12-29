from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, time, date
from typing import List, Dict, Any, Tuple, Optional

import pytz
from sqlalchemy import and_

from models.user_model import User, db
from models.availability_model import Availability
from models.booking_model import Booking
from models.calendar_connection_model import CalendarConnection
from models.event_model import Event


def _parse_iso(dt_str: str) -> datetime:
    """
    Parse ISO datetime string and convert to local naive datetime.
    Handles UTC times (ending in Z) by converting to local timezone (IST).
    """
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


def _round_to_grid(dt: datetime, minutes: int = 30) -> datetime:
    # Round down to a grid (default 30 minutes)
    discard = timedelta(minutes=dt.minute % minutes, seconds=dt.second, microseconds=dt.microsecond)
    return dt - discard


@dataclass(frozen=True)
class Slot:
    start_time: datetime
    end_time: datetime

    def to_public(self, duration_minutes: int) -> Dict[str, Any]:
        return {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_minutes": duration_minutes,
        }


class PublicBookingService:
    """
    Public booking helpers:
    - calculate public available slots
    - (booking creation lives in BookingService)
    """

    @staticmethod
    def _resolve_owner(username: str) -> User:
        owner = User.query.filter(User.public_username == username).first()
        if not owner:
            raise ValueError("Owner not found")
        return owner

    @staticmethod
    def get_slots(username: str, start: str, end: str, duration_minutes: int) -> Dict[str, Any]:
        if duration_minutes not in (30, 60):
            raise ValueError("duration_minutes must be 30 or 60")

        owner = PublicBookingService._resolve_owner(username)

        start_dt = _parse_iso(start)
        end_dt = _parse_iso(end)
        if end_dt <= start_dt:
            raise ValueError("end must be after start")

        # Pull weekly availability rules
        rules = Availability.query.filter_by(owner_id=owner.id).all()
        if not rules:
            return {
                "owner_username": owner.public_username,
                "slots": [],
                "count": 0,
            }

        rules_by_day: Dict[int, Tuple[time, time]] = {r.day_of_week: (r.start_time, r.end_time) for r in rules}

        # Busy intervals = existing bookings + existing events (private details never returned)
        bookings = Booking.query.filter(
            Booking.owner_id == owner.id,
            Booking.start_time < end_dt,
            Booking.end_time > start_dt,
        ).all()
        busy: List[Tuple[datetime, datetime]] = [(b.start_time, b.end_time) for b in bookings]

        events = Event.query.filter(
            Event.user_id == owner.id,
            Event.start_time < end_dt,
            Event.end_time > start_dt,
        ).all()
        busy.extend([(e.start_time, e.end_time) for e in events])

        # Generate slots day-by-day
        slots: List[Slot] = []
        cursor_date: date = start_dt.date()
        last_date: date = end_dt.date()

        while cursor_date <= last_date:
            dow = cursor_date.weekday()  # 0=Mon
            if dow in rules_by_day:
                window_start_t, window_end_t = rules_by_day[dow]
                window_start = datetime.combine(cursor_date, window_start_t)
                window_end = datetime.combine(cursor_date, window_end_t)

                # Intersect with requested [start_dt, end_dt]
                day_start = max(window_start, start_dt)
                day_end = min(window_end, end_dt)

                if day_end > day_start:
                    # Align to 30-min grid to keep slots predictable
                    step = timedelta(minutes=30)
                    slot_len = timedelta(minutes=duration_minutes)

                    t = _round_to_grid(day_start, 30)
                    if t < day_start:
                        t += step

                    while t + slot_len <= day_end:
                        candidate = Slot(start_time=t, end_time=t + slot_len)
                        if not any(_overlaps(candidate.start_time, candidate.end_time, b0, b1) for b0, b1 in busy):
                            slots.append(candidate)
                            # #region agent log
                            try:
                                import os
                                log_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.cursor', 'debug.log')
                                os.makedirs(os.path.dirname(log_path), exist_ok=True)
                                with open(log_path, 'a', encoding='utf-8') as f:
                                    import json
                                    f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"D","location":"public_booking_service.py:123","message":"Generated slot","data":{"slot_start":candidate.start_time.isoformat(),"slot_end":candidate.end_time.isoformat(),"day_end":day_end.isoformat(),"window_start":window_start.isoformat(),"window_end":window_end.isoformat(),"day_of_week":dow,"duration_minutes":duration_minutes},"timestamp":int(datetime.utcnow().timestamp()*1000)}) + '\n')
                            except Exception as e:
                                print(f"DEBUG LOG ERROR: {e}")
                            # #endregion
                        t += step

            cursor_date = cursor_date + timedelta(days=1)

        # Return minimal data only (privacy rule)
        public_slots = [s.to_public(duration_minutes) for s in slots]
        # Determine available providers (used by public booking UI)
        connections = CalendarConnection.query.filter_by(
            user_id=owner.id,
            is_active=True,
            is_connected=True
        ).all()
        available_providers = sorted({conn.provider for conn in connections})

        return {
            "owner_username": owner.public_username,
            "duration_minutes": duration_minutes,
            "slots": public_slots,
            "count": len(public_slots),
            "available_providers": available_providers,
        }


