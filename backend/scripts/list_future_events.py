"""
Utility script to list future events for debugging.

Usage:
    python backend/scripts/list_future_events.py
"""

import os
import sys
from datetime import datetime, timezone

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import create_app  # noqa: E402
from config import Config  # noqa: E402
from models.event_model import Event  # noqa: E402


def list_events():
    app = create_app(Config)
    with app.app_context():
        now = datetime.now(timezone.utc)
        print(f"Current UTC time: {now}", flush=True)

        future_events = (
            Event.query.filter(Event.end_time >= now)
            .order_by(Event.start_time.asc())
            .all()
        )
        print(f"\nFuture events count: {len(future_events)}", flush=True)
        for event in future_events:
            print(
                f"[{event.provider}] {event.title} | start={event.start_time} "
                f"| end={event.end_time} | organizer={event.organizer} "
                f"| provider_event_id={event.provider_event_id}",
                flush=True,
            )

        print("\nAll Microsoft events (latest 10):", flush=True)
        ms_events = (
            Event.query.filter_by(provider='microsoft')
            .order_by(Event.start_time.desc())
            .limit(10)
            .all()
        )
        for event in ms_events:
            print(
                f"MS [{event.title}] start={event.start_time} "
                f"end={event.end_time} organizer={event.organizer} "
                f"provider_event_id={event.provider_event_id}",
                flush=True,
            )


if __name__ == "__main__":
    list_events()

