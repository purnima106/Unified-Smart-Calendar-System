"""
Utility script to remove duplicate event mirror mappings.

Usage:
    python backend/scripts/remove_duplicate_mirror_mappings.py

This script will:
1. Find duplicate rows in `event_mirror_mappings` that share the same
   (original_provider, original_provider_event_id, mirror_provider).
2. Keep the oldest row for each duplicate group and remove the rest.
3. Print a summary of the cleanup operation.
"""

import os
import sys
from collections import defaultdict
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from app import create_app  # noqa: E402
from config import Config  # noqa: E402
from models.event_mirror_mapping_model import EventMirrorMapping, db  # noqa: E402


def remove_duplicates():
    app = create_app(Config)

    with app.app_context():
        print("=" * 70)
        print("Removing duplicate event mirror mappings")
        print("=" * 70)

        mappings = EventMirrorMapping.query.order_by(
            EventMirrorMapping.created_at.asc()
        ).all()
        print(f"Total mappings found: {len(mappings)}")

        groups = defaultdict(list)
        for mapping in mappings:
            key = (
                mapping.original_provider,
                mapping.original_provider_event_id,
                mapping.mirror_provider,
            )
            groups[key].append(mapping)

        duplicates_removed = 0
        duplicate_groups = 0

        for key, group in groups.items():
            if len(group) <= 1:
                continue

            duplicate_groups += 1
            # Keep the first (oldest) mapping, delete the rest
            keep = group[0]
            duplicates = group[1:]

            print("\nDuplicate group detected:")
            print(f"  Original provider: {key[0]}")
            print(f"  Original event ID: {key[1]}")
            print(f"  Mirror provider : {key[2]}")
            print(f"  Keeping mapping ID {keep.id} (created_at={keep.created_at})")

            for dup in duplicates:
                print(
                    f"  -> Removing duplicate mapping ID {dup.id} "
                    f"(created_at={dup.created_at})"
                )
                db.session.delete(dup)
                duplicates_removed += 1

        if duplicates_removed:
            db.session.commit()

        print("\nSummary:")
        print(f"  Duplicate groups processed : {duplicate_groups}")
        print(f"  Duplicate mappings removed : {duplicates_removed}")
        print(f"  Timestamp                  : {datetime.utcnow().isoformat()}Z")

        if duplicates_removed == 0:
            print("  No duplicates were found.")


if __name__ == "__main__":
    remove_duplicates()



