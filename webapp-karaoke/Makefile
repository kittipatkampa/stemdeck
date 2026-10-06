.PHONY: dev backend frontend test deploy-modal modal-smoke

WEBAPP_ROOT := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))
BACKEND := $(WEBAPP_ROOT)backend
FRONTEND := $(WEBAPP_ROOT)frontend
MODAL := $(WEBAPP_ROOT)modal

dev:
	@echo "Starting backend (PIPELINE=local) and frontend..."
	@$(MAKE) -j2 backend frontend

backend:
	cd $(BACKEND) && PIPELINE=local FRONTEND_ORIGIN=http://localhost:5173 \
		uv run --extra pipeline uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

frontend:
	cd $(FRONTEND) && npm run dev

test:
	cd $(BACKEND) && uv run --extra pipeline --group dev pytest -q

deploy-modal:
	cd $(MODAL) && KARAOKE_MODAL_APP=karaoke-maker-dev modal deploy modal_app.py

# Example: MODAL_SECRETS=youtube-cookies make deploy-modal

modal-smoke:
	cd $(MODAL) && modal run modal_app.py::run_job --job-id smoke-$$(date +%s) \
		--youtube-url "https://youtube.com/shorts/senFAeo0RQM"
