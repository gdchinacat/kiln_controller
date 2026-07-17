SERVICE_CMD := HOST=localhost PORT=5000 NON_PERSISTENT=true uv run python -m kiln_controller.service > /tmp/kiln_controller.5000.log 2>&1
PIDFILE := /tmp/kiln_controller.5000.pid

.PHONY: start_service
start_service:
	@echo "Starting service in the background..."
	@$(SERVICE_CMD) 2>&1 > /dev/null & echo $$! > $(PIDFILE)
	@echo "Service started PID=$$(cat $(PIDFILE))"
	
.PHONY: stop_service
stop_service:
	@PID=$$(cat $(PIDFILE))
	@echo "stopping $$(cat $(PIDFILE))"
	@kill $$(cat $(PIDFILE)) && rm $(PIDFILE)
	@echo "service stopped"

.PHONY: test
test: mock_tests live_tests

.PHONY: mock_tests live_tests
mock_tests: mock_clean_test mock_dirty_test
live_tests: live_clean_test live_dirty_test

.PHONY: mock_dirty_test
mock_dirty_test:
	LIVE_SERVICE=false SKIP_CLEANUP=true uv run pytest

.PHONY: mock_clean_test
mock_clean_test:
	LIVE_SERVICE=false SKIP_CLEANUP=false uv run pytest

.PHONY: live_dirty_test
live_dirty_test:
	make start_service
	LIVE_SERVICE=true SKIP_CLEANUP=true uv run pytest
	make stop_service

.PHONY: live_clean_test
live_clean_test:
	make start_service
	LIVE_SERVICE=true SKIP_CLEANUP=false uv run pytest
	make stop_service
