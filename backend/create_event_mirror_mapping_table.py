#!/usr/bin/env python3
"""
One-time migration script to create the event_mirror_mappings table.

Run from the backend directory:
    python create_event_mirror_mapping_table.py
"""

from sqlalchemy import text

from app import create_app
from models.event_mirror_mapping_model import EventMirrorMapping  # noqa: F401
from models.user_model import db


CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS event_mirror_mappings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    original_provider VARCHAR(20) NOT NULL,
    original_event_id INTEGER REFERENCES events(id) ON DELETE SET NULL,
    original_provider_event_id VARCHAR(200) NOT NULL,
    mirror_provider VARCHAR(20) NOT NULL,
    mirror_event_id INTEGER REFERENCES events(id) ON DELETE SET NULL,
    mirror_provider_event_id VARCHAR(200) NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_UNIQUE_CONSTRAINT = """
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_original_mirror_provider_event'
    ) THEN
        ALTER TABLE event_mirror_mappings
        ADD CONSTRAINT uq_original_mirror_provider_event
        UNIQUE (original_provider, original_provider_event_id, mirror_provider);
    END IF;
END $$;
"""

CREATE_INDEXES = [
    """
    CREATE INDEX IF NOT EXISTS idx_original_provider_event_id
    ON event_mirror_mappings (original_provider, original_provider_event_id);
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_mirror_provider_event_id
    ON event_mirror_mappings (mirror_provider, mirror_provider_event_id);
    """
]


def run():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as connection:
            print("Creating event_mirror_mappings table if it does not exist...")
            connection.execute(text(CREATE_TABLE_SQL))
            connection.execute(text(CREATE_UNIQUE_CONSTRAINT))
            for stmt in CREATE_INDEXES:
                connection.execute(text(stmt))
        print("✅ event_mirror_mappings table is ready.")


if __name__ == '__main__':
    run()

