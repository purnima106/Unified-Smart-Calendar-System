from datetime import time
from typing import List, Dict, Any

from models.user_model import db, User
from models.availability_model import Availability


def _parse_hhmm(value: str) -> time:
    if not isinstance(value, str) or ":" not in value:
        raise ValueError("Time must be in HH:MM format")
    hh, mm = value.split(":", 1)
    return time(hour=int(hh), minute=int(mm))


class AvailabilityService:
    """CRUD for owner availability (stored in app DB)."""

    @staticmethod
    def get_owner_availability(owner_id: int) -> Dict[str, Any]:
        owner = User.query.get(owner_id)
        if not owner:
            raise ValueError("Owner not found")

        rules = Availability.query.filter_by(owner_id=owner_id).order_by(Availability.day_of_week).all()
        return {
            "owner_id": owner_id,
            "public_username": owner.public_username,
            "default_slot_duration_minutes": owner.default_slot_duration_minutes or 30,
            "availability": [r.to_dict() for r in rules],
        }

    @staticmethod
    def set_owner_availability(owner_id: int, payload: Dict[str, Any]) -> Dict[str, Any]:
        owner = User.query.get(owner_id)
        if not owner:
            raise ValueError("Owner not found")

        default_duration = int(payload.get("default_slot_duration_minutes", owner.default_slot_duration_minutes or 30))
        if default_duration not in (30, 60):
            raise ValueError("default_slot_duration_minutes must be 30 or 60")

        items: List[Dict[str, Any]] = payload.get("availability") or []
        if not isinstance(items, list):
            raise ValueError("availability must be a list")

        # Validate + normalize by day
        normalized: Dict[int, Dict[str, Any]] = {}
        for item in items:
            day = int(item.get("day_of_week"))
            if day < 0 or day > 6:
                raise ValueError("day_of_week must be 0-6 (0=Mon ... 6=Sun)")

            start_t = _parse_hhmm(item.get("start_time"))
            end_t = _parse_hhmm(item.get("end_time"))
            if (end_t.hour, end_t.minute) <= (start_t.hour, start_t.minute):
                raise ValueError("end_time must be after start_time")

            normalized[day] = {"day_of_week": day, "start_time": start_t, "end_time": end_t}

        # Upsert availability: simplest approach = delete + insert (small data)
        Availability.query.filter_by(owner_id=owner_id).delete()
        for day, data in normalized.items():
            db.session.add(
                Availability(
                    owner_id=owner_id,
                    day_of_week=day,
                    start_time=data["start_time"],
                    end_time=data["end_time"],
                )
            )

        owner.default_slot_duration_minutes = default_duration
        if not owner.public_username:
            owner.ensure_public_username()

        db.session.commit()
        return AvailabilityService.get_owner_availability(owner_id)


