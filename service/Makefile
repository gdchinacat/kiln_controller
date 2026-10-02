# 1. Default PORT to 5000 if not explicitly set via environment or command line
PORT ?= 5000

PIDFILE = /tmp/kiln_controller.$(PORT).pid
LOGFILE = /tmp/kiln_controller.$(PORT).log

SERVICE_CMD ?= uv run uvicorn kiln_controller.service.main:app --host 0.0.0.0 --port $(PORT) --ssl-keyfile ./key.pem --ssl-certfile ./cert.pem --timeout-keep-alive 300 >> $(LOGFILE) 2>&1
TEST_SERVICE_CMD ?= TEST_SERVICE=true uv run uvicorn kiln_controller.service.main:app --host 0.0.0.0 --port $(PORT) > $(LOGFILE) 2>&1


.PHONY: all
all:

.PHONY: start_service
start_service: stop_service
	@echo "Starting service on port $(PORT) in the background..."
	$(SERVICE_CMD) 2>&1 > /dev/null & echo $$! > $(PIDFILE)
	@sleep 2
	@echo "Service started on port $(PORT) PID=$$(cat $(PIDFILE))"

.PHONY: start_service_test
start_service_test: PORT := 50001
start_service_test:
	@LOGFILE= PORT=$(PORT) SERVICE_CMD='$(TEST_SERVICE_CMD)' $(MAKE) start_service

.PHONY: stop_service_test
stop_service_test: PORT := 50001
stop_service_test:
	@$(MAKE) stop_service PORT=${PORT}

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
live_dirty_test: stop_service_test
	@$(MAKE) start_service_test
	@SERVICE_PORT=$(PORT) LIVE_SERVICE=true SKIP_CLEANUP=true uv run pytest -s
	@$(MAKE) stop_service_test

.PHONY: live_clean_test
live_clean_test: PORT := 50001
live_clean_test: stop_service_test
	@$(MAKE) start_service_test
	@SERVICE_PORT=$(PORT) LIVE_SERVICE=true SKIP_CLEANUP=false uv run pytest -s
	@$(MAKE) stop_service_test
