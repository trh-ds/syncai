.PHONY: backend-dev frontend-dev seed poller auth-start

backend-dev:
	cd backend && .venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

frontend-dev:
	cd frontend && npm run dev

seed:
	cd backend && .venv\Scripts\python.exe -m seed.run_seed

poller:
	cd backend && .venv\Scripts\python.exe -m gmail.poller

auth-start:
	@echo "Open http://localhost:8000/auth/start in your browser"
