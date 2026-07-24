"""Self-checks for the compliance + billing paths. Run: python tests/test_saas.py (or pytest).

Uses in-memory SQLite — no external services, no LLM calls.
"""

import hashlib
import hmac
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

from core.database import Base, engine, SessionLocal  # noqa: E402
from models.customer import Customer  # noqa: E402
from services import compliance  # noqa: E402
from services.customer_service import DEAL_VALUE_BY_SCORE, FORECAST_WEIGHT, estimate_deal_value, set_lead_score  # noqa: E402
from api.v1.billing import _verify_stripe_signature  # noqa: E402
from core.config import settings  # noqa: E402


def test_footer_and_opt_out():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        c = Customer(email="lead@example.com", name="Lead", source="email", lead_score="cold")
        db.add(c)
        db.commit()
        db.refresh(c)

        footer = compliance.build_footer(c)
        assert settings.BUSINESS_NAME in footer, "footer missing business name"
        assert settings.BUSINESS_ADDRESS in footer, "footer missing physical address"
        assert c.unsubscribe_token in footer, "footer missing unsubscribe link"
        assert compliance.can_send(c) is True

        # Unsubscribe via token → hard send block
        out = compliance.opt_out(db, c.unsubscribe_token)
        assert out is not None and out.opted_out is True
        assert compliance.can_send(c) is False
        # Bad token → None, no crash
        assert compliance.opt_out(db, "bogus-token") is None
        # Audit log writes
        compliance.log_send(db, c.email, footer, org_id=None)
    finally:
        db.close()


def test_stripe_signature():
    settings.STRIPE_WEBHOOK_SECRET = "whsec_test"
    body = b'{"type":"checkout.session.completed"}'
    ts = "1700000000"
    sig = hmac.new(b"whsec_test", f"{ts}.{body.decode()}".encode(), hashlib.sha256).hexdigest()
    assert _verify_stripe_signature(body, f"t={ts},v1={sig}") is False  # too old (>5 min)
    import time

    ts = str(int(time.time()))
    sig = hmac.new(b"whsec_test", f"{ts}.{body.decode()}".encode(), hashlib.sha256).hexdigest()
    assert _verify_stripe_signature(body, f"t={ts},v1={sig}") is True
    assert _verify_stripe_signature(body, f"t={ts},v1=deadbeef") is False
    assert _verify_stripe_signature(b'{"tampered":1}', f"t={ts},v1={sig}") is False


def test_deal_value_and_forecast():
    assert estimate_deal_value("hot") == DEAL_VALUE_BY_SCORE["hot"]
    assert estimate_deal_value("nonsense") == 500.0
    c = Customer(email="x@example.com", source="chat", lead_score="cold")
    set_lead_score(c, "hot")
    assert c.lead_score == "hot" and c.deal_value_estimate == DEAL_VALUE_BY_SCORE["hot"]
    # Stage-weighted: hot counts 70%, cold 5%
    assert FORECAST_WEIGHT["hot"] > FORECAST_WEIGHT["warm"] > FORECAST_WEIGHT["cold"]
    forecast = DEAL_VALUE_BY_SCORE["hot"] * FORECAST_WEIGHT["hot"]
    assert 0 < forecast < DEAL_VALUE_BY_SCORE["hot"]


if __name__ == "__main__":
    test_footer_and_opt_out()
    test_stripe_signature()
    test_deal_value_and_forecast()
    print("All self-checks passed")
