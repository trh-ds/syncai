"""Wave-3 independent verification harness (does not modify app code).

Part 1: boot the UNMODIFIED app (uvicorn main:app) -> proves startup behaviour.
Part 2: boot via collection-name shim (verify/app_shim.py renames Chroma
        collection 'kb' -> 'kbverify'; everything else is stock app code)
        -> full endpoint contract tests.
Part 3: realistic-but-invalid GROQ_API_KEY -> documents LLM failure status.

Run from repo root:  backend\\venv\\Scripts\\python.exe verify\\verify_wave3.py
Exit 0 = all contract checks pass (deviations printed but reported, not failed).
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
PORT = 8031
BASE = f"http://127.0.0.1:{PORT}"
TMP = Path(tempfile.mkdtemp())
DB_FILE = TMP / "verify.db"
DB_URL = f"sqlite+pysqlite:///{DB_FILE.as_posix()}"
CHROMA_DIR = TMP / "chroma"

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}  {detail}")


def note(name, detail):
    print(f"NOTE  {name}  {detail}")


def is_error_shape(b):
    return (
        isinstance(b, dict)
        and isinstance(b.get("error"), dict)
        and isinstance(b["error"].get("code"), str)
        and isinstance(b["error"].get("message"), str)
    )


def kill(proc):
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def base_env(groq_key):
    env = dict(
        os.environ,
        DATABASE_URL=DB_URL,
        GROQ_API_KEY=groq_key,
        CHROMA_PATH=str(CHROMA_DIR),
        KB_SEED_FILE=str(BACKEND / "mock_kb.txt"),
        CORS_ORIGINS="http://localhost:3000",
    )
    return env


def wait_ready(proc, timeout=180):
    for _ in range(int(timeout * 2)):
        try:
            if httpx.get(f"{BASE}/health", timeout=1).status_code == 200:
                return True
        except Exception:
            pass
        if proc.poll() is not None:
            return False
        time.sleep(0.5)
    return False


def part1_stock_boot():
    """Unmodified app, stock config: does it even start?"""
    print("\n--- Part 1: unmodified app boot (main:app, collection 'kb') ---", flush=True)
    env = base_env("gsk_...")
    log = open(TMP / "part1.log", "w")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--port", str(PORT)],
        cwd=BACKEND, env=env, stdout=log, stderr=subprocess.STDOUT,
    )
    ready = wait_ready(proc, timeout=60)
    alive = proc.poll() is None
    check("stock app boots & serves /health", alive and ready,
          "alive=%s ready=%s" % (alive, ready))
    kill(proc)
    log.close()
    if not ready:
        tail = (TMP / "part1.log").read_text(errors="replace")[-800:].replace("\n", " | ")
        note("stock boot failure tail", tail)


def seed_row():
    os.environ["DATABASE_URL"] = DB_URL
    sys.path.insert(0, str(BACKEND))
    os.chdir(BACKEND)
    from core.database import SessionLocal, init_db
    from models.email import Email
    init_db()
    rid = uuid.uuid4()
    db = SessionLocal()
    db.add(Email(
        id=rid, sender="seed@example.com", sender_name="Seed",
        subject="Seeded subject", body="Seeded body", intent="Sales",
        summary="Seeded summary.", ai_draft="Hi Seed, ...", status="pending",
    ))
    db.add(Email(
        sender="spam@example.com", sender_name=None,
        subject="WIN BIG", body="click now", intent="Spam",
        summary="Spam message.", ai_draft=None, status="pending",
    ))
    db.commit()
    db.close()
    return rid


def boot_shim(groq_key):
    env = base_env(groq_key)
    env["PYTHONPATH"] = str(ROOT / "verify")
    log = open(TMP / "shim.log", "w")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app_shim:app", "--port", str(PORT)],
        cwd=BACKEND, env=env, stdout=log, stderr=subprocess.STDOUT,
    )
    if not wait_ready(proc, timeout=120):
        kill(proc)
        log.close()
        out = (TMP / "shim.log").read_text(errors="replace")
        raise RuntimeError(f"shim server failed to start:\n{out[-2000:]}")
    return proc


EMAIL_KEYS = {"id", "sender", "sender_name", "subject", "body", "intent",
              "summary", "ai_draft", "status", "created_at", "updated_at"}


def part2_endpoints(rid):
    print("\n--- Part 2: endpoint contract tests (placeholder key, shimmed boot) ---")
    proc = boot_shim("gsk_...")
    try:
        c = httpx.Client(base_url=BASE, timeout=30)

        r = c.get("/health")
        check("GET /health 200 {status:ok}", r.status_code == 200 and r.json() == {"status": "ok"}, str(r.status_code))

        r = c.get("/api/v1/emails")
        body = r.json()
        check("GET /emails 200 array", r.status_code == 200 and isinstance(body, list), str(r.status_code))
        if isinstance(body, list) and body:
            e0 = next((e for e in body if e.get("id") == str(rid)), body[0])
            check("email object keys == contract", set(e0.keys()) == EMAIL_KEYS, f"extra/missing: {set(e0.keys()) ^ EMAIL_KEYS}")
            check("newest first", all(body[i]["created_at"] >= body[i+1]["created_at"] for i in range(len(body)-1)), "")
            check("timestamps end with Z", e0["created_at"].endswith("Z") and e0["updated_at"].endswith("Z"), e0["created_at"])
            spam = next((e for e in body if e.get("intent") == "Spam"), None)
            check("spam row ai_draft null", spam is not None and spam["ai_draft"] is None, "")

        r = c.get("/api/v1/emails", params={"status": "pending"})
        check("GET /emails?status=pending filter", r.status_code == 200 and all(e["status"] == "pending" for e in r.json()), str(r.status_code))

        r = c.get("/api/v1/emails", params={"status": "bogus"})
        check("GET /emails?status=bogus -> 422 error shape", r.status_code == 422 and is_error_shape(r.json()), f"{r.status_code} {r.text[:100]}")

        r = c.get(f"/api/v1/emails/{rid}")
        check("GET /emails/{id} 200", r.status_code == 200 and r.json()["id"] == str(rid), str(r.status_code))

        r = c.get(f"/api/v1/emails/{uuid.uuid4()}")
        check("GET unknown id -> 404 NOT_FOUND shape", r.status_code == 404 and r.json().get("error", {}).get("code") == "NOT_FOUND", f"{r.status_code} {r.text[:100]}")

        r = c.get("/api/v1/emails/not-a-uuid")
        check("GET malformed id -> 422 error shape", r.status_code == 422 and is_error_shape(r.json()), str(r.status_code))

        # PATCH
        r = c.patch(f"/api/v1/emails/{rid}", json={"ai_draft": "edited text", "status": "approved"})
        ok = r.status_code == 200 and r.json()["ai_draft"] == "edited text" and r.json()["status"] == "approved"
        check("PATCH happy path 200 updated object", ok, str(r.status_code))
        if ok and set(r.json().keys()) == EMAIL_KEYS:
            pass
        elif ok:
            check("PATCH response keys == contract", False, f"{set(r.json().keys()) ^ EMAIL_KEYS}")

        r = c.patch(f"/api/v1/emails/{rid}", json={})
        check("PATCH empty body -> 422 error shape", r.status_code == 422 and is_error_shape(r.json()), f"{r.status_code} {r.text[:100]}")

        r = c.patch(f"/api/v1/emails/{rid}", json={"status": "bogus"})
        check("PATCH invalid status enum -> 422 error shape", r.status_code == 422 and is_error_shape(r.json()), str(r.status_code))

        r = c.patch(f"/api/v1/emails/{rid}", json={"ai_draft": 123})
        check("PATCH wrong type -> 422 error shape", r.status_code == 422 and is_error_shape(r.json()), str(r.status_code))

        r = c.patch(f"/api/v1/emails/{uuid.uuid4()}", json={"status": "approved"})
        check("PATCH unknown id -> 404 NOT_FOUND", r.status_code == 404 and r.json().get("error", {}).get("code") == "NOT_FOUND", str(r.status_code))

        r = c.patch(f"/api/v1/emails/{rid}", content=b"{bad", headers={"Content-Type": "application/json"})
        check("PATCH malformed JSON -> 422 error shape", r.status_code == 422 and is_error_shape(r.json()), str(r.status_code))

        r = c.patch(f"/api/v1/emails/{rid}", json={"status": "pending"})
        note("PATCH approved->pending reverse transition", f"HTTP {r.status_code} (DATA_MODELS forbids; 200 = not enforced)")

        # Webhook with placeholder key -> agents raise RuntimeError before LLM
        r = c.post("/api/v1/webhooks/email", json={"sender": "jane@acme.com", "subject": "Pricing", "body": "Cost?"})
        check("webhook placeholder key -> 502 LLM error shape",
              r.status_code == 502 and is_error_shape(r.json()), f"{r.status_code} {r.text[:150]}")
        if r.status_code == 502:
            note("webhook 502 code", r.json()["error"]["code"])

        r = c.post("/api/v1/webhooks/email", content=b"{no", headers={"Content-Type": "application/json"})
        check("webhook malformed JSON -> 422 error shape", r.status_code == 422 and is_error_shape(r.json()), str(r.status_code))

        r = c.post("/api/v1/webhooks/email", json={"sender": "a@b.com"})
        check("webhook missing fields -> 422 error shape", r.status_code == 422 and is_error_shape(r.json()), str(r.status_code))

        r = c.post("/api/v1/webhooks/email", json={"sender": 123, "subject": "s", "body": "b"})
        check("webhook wrong types -> 4xx error shape", r.status_code in (400, 422) and is_error_shape(r.json()), str(r.status_code))

        # Demo
        r = c.post("/api/v1/demo/run", json={"url": "http://127.0.0.1:9/nope", "sender_name": "John", "email_body": "SEO?"})
        check("demo unreachable URL -> 502 SCRAPE_FAILED shape",
              r.status_code == 502 and r.json().get("error", {}).get("code") == "SCRAPE_FAILED", f"{r.status_code} {r.text[:150]}")

        r = c.post("/api/v1/demo/run", json={"url": "https://example.com"})
        check("demo missing fields -> 422 error shape", r.status_code == 422 and is_error_shape(r.json()), str(r.status_code))

        r = c.post("/api/v1/demo/run", content=b"x", headers={"Content-Type": "application/json"})
        check("demo malformed JSON -> 422 error shape", r.status_code == 422 and is_error_shape(r.json()), str(r.status_code))

        # CORS
        r = c.options("/api/v1/emails", headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"})
        check("CORS allows http://localhost:3000", r.headers.get("access-control-allow-origin") == "http://localhost:3000",
              f"acao={r.headers.get('access-control-allow-origin')}")
        r = c.options("/api/v1/emails", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"})
        check("CORS rejects unknown origin", r.headers.get("access-control-allow-origin") != "http://evil.example" and r.headers.get("access-control-allow-origin") != "*",
              f"acao={r.headers.get('access-control-allow-origin')}")
    finally:
        kill(proc)


def part3_invalid_key():
    print("\n--- Part 3: realistic-but-invalid GROQ_API_KEY ---")
    proc = boot_shim("gsk_invalid_dummy_key_0000000000000000000000000000000000")
    try:
        c = httpx.Client(base_url=BASE, timeout=90)
        r = c.post("/api/v1/webhooks/email", json={"sender": "jane@acme.com", "subject": "Pricing", "body": "Cost?"})
        note("webhook invalid key", f"HTTP {r.status_code} body={r.text[:200]}")
        check("webhook invalid key -> 502 error shape (README promise)",
              r.status_code == 502 and is_error_shape(r.json()), f"{r.status_code}")
    finally:
        kill(proc)


if __name__ == "__main__":
    part1_stock_boot()
    rid = seed_row()
    part2_endpoints(rid)
    part3_invalid_key()
    failed = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} passed")
    if failed:
        print("FAILED:", *failed, sep="\n  - ")
    sys.exit(1 if failed else 0)
