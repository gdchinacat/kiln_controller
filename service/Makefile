# 1. Default PORT to 5000 if not explicitly set via environment or command line
PORT ?= 5000

PIDFILE = /tmp/kiln_controller.$(PORT).pid
LOGFILE = /tmp/kiln_controller.$(PORT).log
DB_URL = "sqlite+aiosqlite:///kiln_controller.db"

SERVICE_CMD ?= DB_URL=$(DB_URL) uv run uvicorn kiln_controller.service.main:app --host 0.0.0.0 --port $(PORT) --ssl-keyfile ./key.pem --ssl-certfile ./cert.pem --timeout-keep-alive 300 >> $(LOGFILE) 2>&1


.PHONY: all
all:

.PHONY: start_service
start_service: stop_service
	@echo "Starting service on port $(PORT) in the background..."
	$(SERVICE_CMD) 2>&1 > /dev/null & echo $$! > $(PIDFILE)
	@sleep 2
	@echo "Service started on port $(PORT) PID=$$(cat $(PIDFILE))"

.PHONY: stop_service
stop_service:
	@if [ -f $(PIDFILE) ]; then \
		PID=$$(cat $(PIDFILE)); \
		echo "Stopping PID $$PID on port $(PORT)..."; \
		kill $$PID && rm -f $(PIDFILE); \
		sleep 1; \
		kill -INT $$PID 2>/dev/null; \
		while kill -0 $$PID 2>/dev/null;  do echo -n . ; sleep 1; done; \
		rm -f $(PIDFILE); \
		echo "Service on port $(PORT) stopped"; \
	else \
		echo "No PID file found for port $(PORT)"; \
	fi

.PHONY: test
test:
	uv run pytest -s -n 4 .

