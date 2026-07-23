"""ASDR backend verification harness.

Boots uvicorn (sqlite DATABASE_URL, temp Chroma dir) in two phases:
  A: placeholder GROQ_API_KEY -> expect 502 LLM_ERROR on LLM paths
  B: realistic-but-invalid GROQ_API_KEY -> documents actual error code
Seeds one email row directly into sqlite to test GET/PATCH happy paths
(webhook 201 can't be tested without a real Groq key).

Run:  python verify/run_backend_tests.py
Exit code 0 if all contract-mandated checks pass, 1 otherwise.
"""
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
PORT = 8017
BASE = f"http://127.0.0.1:{PORT}"
DB_FILE = Path(tempfile.mkdtemp()) / "verify.db"
CHROMA_DIR = tempfile.mkdtemp()
DB_URL = f"sqlite+pysqlite:///{DB_FILE.as_posix()}"

results = []  # (name, ok, detail)


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")


def is_error_shape(body):
    return (
        isinstance(body, dict)
        and isinstance(body.get("error"), dict)
        and isinstance(body["error"].get("code"), str)
        and isinstance(body["error"].get("message"), str)
    )


def seed_row():
    """Insert one pending email directly via the app's own models."""
    os.environ["DATABASE_URL"] = DB_URL
    sys.path.insert(0, str(BACKEND))
    os.chdir(BACKEND)
    from core.database import SessionLocal, init_db
    from models.email import Email

    init_db()
    rid = uuid.uuid4()
    db = SessionLocal()
    db.add(
        Email(
            id=rid,
            sender="seed@example.com",
            sender_name="Seed",
            subject="Seeded subject",
            body="Seeded body",
            intent="Sales",
            summary="Seeded summary.",
            ai_draft="Hi Seed, ...",
            status="pending",
        )
    )
    db.commit()
    db.close()
    return rid


def boot(groq_key):
    env = dict(
        os.environ,
        DATABASE_URL=DB_URL,
        GROQ_API_KEY=groq_key,
        CHROMA_PATH=CHROMA_DIR,
        KB_SEED_FILE=str(BACKEND / "mock_kb.txt"),
        CORS_ORIGINS="http://localhost:3000",
    )
    env["PYTHONPATH"] = str(Path(__file__).resolve().parent)
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app_shim:app", "--port", str(PORT)],
        cwd=BACKEND,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    for _ in range(360):
        try:
            if httpx.get(f"{BASE}/health", timeout=1).status_code == 200:
                return proc
        except Exception:
            pass
        if proc.poll() is not None:
            out = proc.stdout.read() if proc.stdout else ""
            raise RuntimeError(f"server died:\n{out[-3000:]}")
        time.sleep(0.5)
    kill(proc)
    out = proc.stdout.read() if proc.stdout else ""
    raise RuntimeError(f"server did not start in 180s:\n{out[-3000:]}")


def kill(proc):
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def phase_a(rid):
    print("\n--- Phase A: placeholder GROQ_API_KEY ---")
    proc = boot("gsk_...")
    try:
        c = httpx.Client(base_url=BASE, timeout=30)

        r = c.get("/health")
        check("health", r.status_code == 200 and r.json() == {"status": "ok"}, f"{r.status_code} {r.text[:80]}")

        r = c.get("/api/v1/emails")
        body = r.json()
        check("list emails 200 array", r.status_code == 200 and isinstance(body, list), f"{r.status_code}")
        seeded = next((e for e in body if e.get("id") == str(rid)), None) if isinstance(body, list) else None
        check(
            "seeded row fields match contract",
            seeded is not None
            and set(seeded.keys())
            == {"id", "sender", "sender_name", "subject", "body", "intent", "summary", "ai_draft", "status", "created_at", "updated_at"},
            f"keys={sorted(seeded.keys()) if seeded else None}",
        )
        if seeded:
            check("timestamps ISO Z", seeded["created_at"].endswith("Z") and seeded["updated_at"].endswith("Z"),
                  f"created_at={seeded['created_at']}")

        r = c.get("/api/v1/emails", params={"status": "pending"})
        check("list filter pending", r.status_code == 200 and all(e["status"] == "pending" for e in r.json()), f"{r.status_code}")

        r = c.get("/api/v1/emails", params={"status": "bogus"})
        check("list invalid status -> 422 shape", r.status_code == 422 and is_error_shape(r.json()), f"{r.status_code} {r.text[:120]}")

        r = c.get(f"/api/v1/emails/{uuid.uuid4()}")
        check("get unknown id -> 404 NOT_FOUND", r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND", f"{r.status_code} {r.text[:120]}")

        r = c.get("/api/v1/emails/not-a-uuid")
        check("get malformed id -> error shape (422 expected)", r.status_code in (404, 422) and is_error_shape(r.json()), f"{r.status_code}")

        r = c.post("/api/v1/webhooks/email", json={"sender": "jane@acme.com", "subject": "Pricing", "body": "Cost?"})
        check("webhook placeholder key -> 502 LLM_ERROR", r.status_code == 502 and r.json()["error"]["code"] == "LLM_ERROR", f"{r.status_code} {r.text[:160]}")

        r = c.post("/api/v1/webhooks/email", content=b"{not json", headers={"Content-Type": "application/json"})
        check("webhook malformed JSON -> 422 shape", r.status_code == 422 and is_error_shape(r.json()), f"{r.status_code} {r.text[:120]}")

        r = c.post("/api/v1/webhooks/email", json={"sender": "a@b.com"})
        check("webhook missing fields -> 422 shape", r.status_code == 422 and is_error_shape(r.json()), f"{r.status_code}")

        r = c.post("/api/v1/webhooks/email", json={"sender": 123, "subject": "s", "body": "b"})
        check("webhook wrong types -> 4xx shape", r.status_code in (400, 422) and is_error_shape(r.json()), f"{r.status_code}")

        r = c.post("/api/v1/webhooks/email", json={"sender": "", "subject": "s", "body": "b"})
        check("webhook empty sender -> 422 shape", r.status_code == 422 and is_error_shape(r.json()), f"{r.status_code}")

        r = c.patch(f"/api/v1/emails/{rid}", json={})
        check("patch empty body -> 422 shape", r.status_code == 422 and is_error_shape(r.json()), f"{r.status_code} {r.text[:120]}")

        r = c.patch(f"/api/v1/emails/{rid}", json={"status": "bogus"})
        check("patch invalid status enum -> 422 shape", r.status_code == 422 and is_error_shape(r.json()), f"{r.status_code}")

        r = c.patch(f"/api/v1/emails/{uuid.uuid4()}", json={"status": "approved"})
        check("patch unknown id -> 404 NOT_FOUND", r.status_code == 404 and r.json()["error"]["code"] == "NOT_FOUND", f"{r.status_code}")

        before = c.get(f"/api/v1/emails/{rid}").json()
        time.sleep(1.1)
        r = c.patch(f"/api/v1/emails/{rid}", json={"ai_draft": "edited text", "status": "approved"})
        ok = r.status_code == 200 and r.json()["ai_draft"] == "edited text" and r.json()["status"] == "approved"
        check("patch happy path 200", ok, f"{r.status_code}")
        if ok:
            check("patch touches updated_at", r.json()["updated_at"] > before["updated_at"],
                  f"{before['updated_at']} -> {r.json()['updated_at']}")

        r = c.patch(f"/api/v1/emails/{rid}", json={"status": "pending"})
        check("patch reverse transition approved->pending (contract forbids)", r.status_code != 200, f"{r.status_code} (200 = deviation)")

        r = c.post("/api/v1/demo/run", json={"url": "http://127.0.0.1:9/nope", "sender_name": "John", "email_body": "SEO?"})
        check("demo unreachable URL -> 502 SCRAPE_FAILED", r.status_code == 502 and r.json()["error"]["code"] == "SCRAPE_FAILED", f"{r.status_code} {r.text[:160]}")

        r = c.post("/api/v1/demo/run", json={"url": "https://example.com"})
        check("demo missing fields -> 422 shape", r.status_code == 422 and is_error_shape(r.json()), f"{r.status_code}")

        r = c.options(
            "/api/v1/emails",
            headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
        )
        check("CORS allows frontend origin", r.headers.get("access-control-allow-origin") == "http://localhost:3000",
              f"acao={r.headers.get('access-control-allow-origin')}")

        r = c.options(
            "/api/v1/emails",
            headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"},
        )
        check("CORS rejects other origins", r.headers.get("access-control-allow-origin") in (None, "http://localhost:3000"),
              f"acao={r.headers.get('access-control-allow-origin')}")
    finally:
        kill(proc)


def phase_b():
    print("\n--- Phase B: realistic-but-invalid GROQ_API_KEY ---")
    proc = boot("gsk_invalid_dummy_key_0000000000000000000000000000000000")
    try:
        c = httpx.Client(base_url=BASE, timeout=60)
        r = c.post("/api/v1/webhooks/email", json={"sender": "jane@acme.com", "subject": "Pricing", "body": "Cost?"})
        # Contract/README promise 502 LLM_ERROR for LLM failures. Document reality.
        ok = r.status_code == 502 and is_error_shape(r.json()) and r.json()["error"]["code"] == "LLM_ERROR"
        check("webhook invalid key -> 502 LLM_ERROR", ok, f"actual: {r.status_code} {r.text[:200]}")

        r = c.post("/api/v1/demo/run", json={"url": "http://127.0.0.1:9/nope", "sender_name": "J", "email_body": "x"})
        check("demo scrape still short-circuits before LLM", r.status_code == 502 and r.json()["error"]["code"] == "SCRAPE_FAILED", f"{r.status_code}")
    finally:
        kill(proc)


if __name__ == "__main__":
    rid = seed_row()
    phase_a(rid)
    phase_b()
    failed = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("FAILED:", *failed, sep="\n  - ")
    sys.exit(1 if failed else 0)
