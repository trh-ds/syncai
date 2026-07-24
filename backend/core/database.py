import logging

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from core.config import settings

logger = logging.getLogger("db")

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


# ponytail: hand-rolled idempotent column adds — Alembic is overkill for one additive pass
_COLUMN_ADDS = [
    "ALTER TABLE emails ADD COLUMN IF NOT EXISTS org_id UUID",
    "ALTER TABLE emails ADD COLUMN IF NOT EXISTS reply_intent TEXT",
    "ALTER TABLE customers ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id)",
    "ALTER TABLE customers ADD COLUMN IF NOT EXISTS consent_source TEXT",
    "ALTER TABLE customers ADD COLUMN IF NOT EXISTS consent_timestamp TIMESTAMPTZ",
    "ALTER TABLE customers ADD COLUMN IF NOT EXISTS opted_out BOOLEAN NOT NULL DEFAULT false",
    "ALTER TABLE customers ADD COLUMN IF NOT EXISTS unsubscribe_token TEXT",
    "ALTER TABLE customers ADD COLUMN IF NOT EXISTS deal_value_estimate DOUBLE PRECISION",
    "ALTER TABLE customers ADD COLUMN IF NOT EXISTS job_title TEXT",
    "ALTER TABLE customers ADD COLUMN IF NOT EXISTS company_size TEXT",
    "ALTER TABLE interactions ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id)",
    "ALTER TABLE meetings ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_customers_unsubscribe_token ON customers(unsubscribe_token)",
]


def init_db() -> None:
    from models import email  # noqa: F401
    from models import customer  # noqa: F401
    from models import org  # noqa: F401

    Base.metadata.create_all(engine)
    for stmt in _COLUMN_ADDS:
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
        except Exception:
            # ponytail: sqlite dev DBs can't IF NOT EXISTS — create_all already covered fresh ones
            logger.debug("migration skipped: %s", stmt)
    _seed_default_org()


def _seed_default_org() -> None:
    """Single-tenant fallback: one org holding the env-based Gmail creds.

    All legacy/unauthenticated traffic is scoped here so the demo keeps working
    with zero config. Real tenants get their own org via signup.
    """
    from models.org import Organization

    db = SessionLocal()
    try:
        default = db.query(Organization).filter(Organization.owner_user_id.is_(None)).first()
        if not default:
            default = Organization(
                name=settings.CLIENT_COMPANY_NAME,
                gmail_refresh_token=settings.GMAIL_REFRESH_TOKEN or None,
                gmail_user_email=settings.GMAIL_USER_EMAIL or None,
            )
            db.add(default)
            db.commit()
            db.refresh(default)
            logger.info("Seeded default org %s", default.id)
        # Backfill pre-existing rows into the default org
        for table in ("emails", "customers", "interactions", "meetings"):
            db.execute(text(f"UPDATE {table} SET org_id = :oid WHERE org_id IS NULL"), {"oid": str(default.id)})
        db.commit()
    finally:
        db.close()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def default_org_id(db) -> "object":
    """Return the single-tenant fallback org id."""
    from models.org import Organization

    org = db.query(Organization).filter(Organization.owner_user_id.is_(None)).first()
    return org.id if org else None
