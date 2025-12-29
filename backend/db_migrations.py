"""
Very small, migration-like helper.

This project historically used db.create_all() without Alembic. For additive schema
changes (new columns/indexes), we apply safe ALTER TABLE statements at startup.

Important: Keep migrations additive + idempotent to avoid breaking existing installs.
"""

from sqlalchemy import text


def _column_exists(db, table_name: str, column_name: str) -> bool:
    engine_name = db.engine.dialect.name

    if engine_name == "sqlite":
        rows = db.session.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
        return any(r[1] == column_name for r in rows)  # r[1] is column name

    # Postgres / others
    rows = db.session.execute(
        text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = :table AND column_name = :col
            LIMIT 1
            """
        ),
        {"table": table_name, "col": column_name},
    ).fetchall()
    return len(rows) > 0


def _index_exists(db, index_name: str) -> bool:
    engine_name = db.engine.dialect.name

    if engine_name == "sqlite":
        rows = db.session.execute(text("PRAGMA index_list(users)")).fetchall()
        # rows: (seq, name, unique, origin, partial)
        return any(r[1] == index_name for r in rows)

    if engine_name == "postgresql":
        rows = db.session.execute(
            text(
                """
                SELECT 1
                FROM pg_indexes
                WHERE indexname = :idx
                LIMIT 1
                """
            ),
            {"idx": index_name},
        ).fetchall()
        return len(rows) > 0

    return False


def apply_migrations(db):
    """
    Apply additive schema updates.
    Call this after db.init_app() and inside app.app_context().
    """
    # Users.public_username + users.default_slot_duration_minutes
    if not _column_exists(db, "users", "public_username"):
        db.session.execute(text("ALTER TABLE users ADD COLUMN public_username VARCHAR(120)"))

    if not _column_exists(db, "users", "default_slot_duration_minutes"):
        db.session.execute(text("ALTER TABLE users ADD COLUMN default_slot_duration_minutes INTEGER DEFAULT 30"))

    # Unique index for public_username (nullable => allowed)
    # (SQLite supports multiple NULLs, Postgres too.)
    idx_name = "ix_users_public_username"
    if not _index_exists(db, idx_name):
        try:
            db.session.execute(text(f"CREATE UNIQUE INDEX {idx_name} ON users(public_username)"))
        except Exception:
            # Index may already exist under a different name; ignore.
            pass

    db.session.commit()


