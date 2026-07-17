
.PHONY: test_service
test_service:
	@make -C service test
	
.PHONY: test
test: test_service
