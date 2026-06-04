"""
SQLAlchemy setup with a *schema-drift detector*.

If the existing DB was created by a previous version of this app and is
missing columns/tables the new code expects, we drop everything and start
fresh. Data is re-fetchable from the upstream API, so wiping a stale local
cache is a safe trade-off for development simplicity.
"""
from sqlalchemy import create_engine, inspect, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from .config import settings

# SQLite is used as a local development cache. Refresh writes a large batch of
# hero/item rows, while the frontend may simultaneously read charts/tables. The
# settings below make SQLite wait for a short period instead of immediately
# failing with "database is locked", and WAL mode allows readers while a writer
# is active. NullPool avoids keeping stale file handles open between requests.
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False, "timeout": 30}
    engine = create_engine(
        settings.database_url,
        connect_args=connect_args,
        future=True,
        poolclass=NullPool,
    )
else:
    engine = create_engine(settings.database_url, future=True)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection, connection_record):
    if settings.database_url.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=30000")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---- expected columns we need on each existing table ----
_REQUIRED_COLS = {
    "balance_flags": {"macro_impact", "mechanical_reasoning"},
    "hero_stats":    {"avg_net_worth", "kda"},
    "heroes":        {"image_url", "role_text", "playstyle"},
    "item_stats":    {"icon_url", "group_key", "exclusive_ids"},
}
_REQUIRED_TABLES = {"item_stats"}


def _schema_is_stale() -> bool:
    """True if the live DB is missing columns/tables we expect."""
    insp = inspect(engine)
    existing_tables = set(insp.get_table_names())
    if _REQUIRED_TABLES - existing_tables:
        return True
    for table, needed in _REQUIRED_COLS.items():
        if table in existing_tables:
            cols = {c["name"] for c in insp.get_columns(table)}
            if needed - cols:
                return True
    return False


def init_db() -> None:
    from . import models  # noqa: F401 (registers models on Base.metadata)
    if _schema_is_stale():
        # Old schema present — drop and recreate. We lose locally cached
        # stats but a single /refresh repopulates them.
        print("[init_db] schema drift detected — dropping and recreating tables")
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
