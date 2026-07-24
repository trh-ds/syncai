"""Boot smoke test: app starts, init_db migrates, key routes respond. Run: python tests/test_boot.py"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import tempfile  # noqa: E402

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_tmp.name}"  # file, not :memory: — TestClient uses threads
os.environ["GROQ_API_KEY"] = ""  # no LLM calls in this test
# Keep the mail poller idle — no Gmail creds in test
for var in ("GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN"):
    os.environ[var] = ""

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402


def test_boot():
    with TestClient(app) as client:
        assert client.get("/health").json() == {"status": "ok"}
        # Org-scoped list endpoints fall back to the default org
        assert client.get("/api/v1/emails").json() == []
        stats = client.get("/api/v1/crm/stats").json()
        assert stats["total_leads"] == 0
        assert "pipeline_forecast" in stats
        # Unsubscribe with bad token → 404, not a crash
        assert client.post("/api/v1/unsubscribe/bogus").status_code == 404
        # Plan endpoint works unauthenticated (default org, starter)
        assert client.get("/api/v1/billing/plan").json()["plan"] == "starter"
    print("Boot smoke test passed")


if __name__ == "__main__":
    test_boot()
