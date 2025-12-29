from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, time, date
from typing import List, Dict, Any, Tuple, Optional

from sqlalchemy import and_

from models.user_model import User, db
from models.availability_model import Availability
from models.booking_model import Booking
from models.event_model import Event


def _parse_iso(dt_str: str) -> datetime:
    # Accept "Z" format from frontend
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00")).replace(tzinfo=None)


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
                        t += step

            cursor_date = cursor_date + timedelta(days=1)

        # Return minimal data only (privacy rule)
        public_slots = [s.to_public(duration_minutes) for s in slots]
        return {
            "owner_username": owner.public_username,
            "duration_minutes": duration_minutes,
            "slots": public_slots,
            "count": len(public_slots),
        }


