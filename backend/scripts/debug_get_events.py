"""
Debug helper to run the get_events logic for a specific user.
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
from models.calendar_connection_model import CalendarConnection  # noqa: E402


def debug_get_events(user_id=2):
    app = create_app(Config)
    with app.app_context():
        connections = CalendarConnection.query.filter_by(
            user_id=user_id, is_active=True, is_connected=True
        ).all()
        print(f"Connections ({len(connections)}): {[c.provider + ':' + c.provider_account_email for c in connections]}", flush=True)

        connected_emails = [conn.provider_account_email for conn in connections]
        connected_providers = list({conn.provider for conn in connections})

        now = datetime.now(timezone.utc)
        query = Event.query.filter(Event.end_time >= now)
        query = query.filter(~Event.title.ilike('[mirror]%'))

        from sqlalchemy import or_, and_

        or_conditions = []
        or_conditions.append(
            and_(Event.user_id == user_id, Event.provider.in_(connected_providers))
        )
        or_conditions.append(
            and_(Event.organizer.in_(connected_emails), Event.organizer != None, Event.organizer != '')  # noqa: E711
        )
        for email in connected_emails:
            or_conditions.append(Event.provider_event_id.like(f"{email}:%"))

        events = query.filter(or_(*or_conditions)).order_by(Event.start_time).all()
        print(f"Events returned: {len(events)}", flush=True)
        for event in events:
            print(
                f"[{event.provider}] {event.title} start={event.start_time} "
                f"end={event.end_time} organizer={event.organizer} "
                f"provider_event_id={event.provider_event_id}",
                flush=True,
            )


if __name__ == "__main__":
    debug_get_events()



