# 1. Default PORT to 5000 if not explicitly set via environment or command line
PORT ?= 5000

PIDFILE := /tmp/kiln_controller.$(PORT).pid
LOGFILE := /tmp/kiln_controller.$(PORT).log
SERVICE_CMD := NON_PERSISTENT=true uv run fastapi dev --host 0.0.0.0 --port $(PORT) src/kiln_controller/service/__main__.py >> $(LOGFILE) 2>&1

.PHONY: start_service
start_service:
	@echo "Starting service on port $(PORT) in the background..."
	@$(SERVICE_CMD) 2>&1 > /dev/null & echo $$! > $(PIDFILE)
	@sleep 1
	@echo "Service started on port $(PORT) PID=$$(cat $(PIDFILE))"

.PHONY: stop_service
stop_service:
	@if [ -f $(PIDFILE) ]; then \
		PID=$$(cat $(PIDFILE)); \
		echo "Stopping PID $$PID on port $(PORT)..."; \
		kill $$PID && rm -f $(PIDFILE); \
		echo "Service on port $(PORT) stopped"; \
	else \
		echo "No PID file found for port $(PORT)"; \
	fi

.PHONY: test
test: mock_tests live_tests

.PHONY: mock_tests live_tests
mock_tests: mock_clean_test mock_dirty_test

# Force PORT=50001 when executing live test targets
live_tests: PORT := 50001
live_tests: live_clean_test live_dirty_test

.PHONY: mock_dirty_test
mock_dirty_test:
	LIVE_SERVICE=false SKIP_CLEANUP=true uv run pytest -s

.PHONY: mock_clean_test
mock_clean_test:
	LIVE_SERVICE=false SKIP_CLEANUP=false uv run pytest -s

.PHONY: live_dirty_test
live_dirty_test: PORT := 50001
live_dirty_test:
	@$(MAKE) start_service PORT=$(PORT)
	SERVICE_PORT=$(PORT) LIVE_SERVICE=true SKIP_CLEANUP=true uv run pytest -s
	@$(MAKE) stop_service PORT=$(PORT)

.PHONY: live_clean_test
live_clean_test: PORT := 50001
live_clean_test:
	@$(MAKE) start_service PORT=$(PORT)
	SERVICE_PORT=$(PORT) LIVE_SERVICE=true SKIP_CLEANUP=false uv run pytest -s
	@$(MAKE) stop_service PORT=$(PORT)