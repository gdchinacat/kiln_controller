BUILD_TYPE := Release

# Define your tool paths based on your Eclipse plugin structure
ESPTOOL := python3 /home/lonnieh/eclipse/eclipse/arduinoPlugin/packages/esp32/tools/esptool_py/4.5.1/esptool.py
PARTITION_GEN := /home/lonnieh/eclipse/eclipse/arduinoPlugin/packages/esp32/hardware/esp32/3.3.11/tools/gen_esp32part.py

# Source paths for core layout
PARTITION_CSV  := /home/lonnieh/eclipse/eclipse/arduinoPlugin/packages/esp32/hardware/esp32/3.3.11/tools/partitions/default.csv

.PHONY: all
all: device docs

.PHONY: monitor
monitor:
	minicom -D /dev/ttyUSB0 -b 921600

.PHONY: device
device:
	make -C $(BUILD_TYPE) main-build
	$(ESPTOOL) --chip esp32 elf2image --flash_mode dio --flash_freq 80m --flash_size 4MB -o $(BUILD_TYPE)/device.bin $(BUILD_TYPE)/device.elf
	python3 $(PARTITION_GEN) -q $(PARTITION_CSV) $(BUILD_TYPE)/device.partitions.bin
	@if [ -f "stable_bootloader.bin" ]; then \
		cp stable_bootloader.bin $(BUILD_TYPE)/device.bootloader.bin; \
	else \
		echo "ERROR: stable_bootloader.bin missing from project root folder."; \
		exit 1; \
	fi

.PHONY: clean
clean:
	make -C $(BUILD_TYPE) clean
	rm -f $(BUILD_TYPE)/*.bin
	rm -rf docs

.PHONY: upload
upload: device
	$(ESPTOOL) --chip esp32 --port /dev/ttyUSB0 --baud 921600 --before default_reset --after hard_reset write_flash -z --flash_mode dio --flash_freq 80m --flash_size 4MB 0x1000 /home/lonnieh/eclipse-workspace/kiln_controller/device/$(BUILD_TYPE)/device.bootloader.bin 0x8000 /home/lonnieh/eclipse-workspace/kiln_controller/device/$(BUILD_TYPE)/device.partitions.bin 0xe000 /home/lonnieh/eclipse/eclipse/arduinoPlugin/packages/esp32/hardware/esp32/3.3.11/tools/partitions/boot_app0.bin 0x10000 /home/lonnieh/eclipse-workspace/kiln_controller/device/$(BUILD_TYPE)/device.bin


# Doxygen Configuration
DOXYGEN  ?= doxygen
DOXYFILE ?= Doxyfile
DOC_DIR  ?= docs

.PHONY: docs docs-clean docs-init docs-view

## Generate Doxygen HTML and LaTeX documentation
docs: $(DOXYFILE)
	@echo "Building documentation..."
	@mkdir -p $(DOC_DIR)
	$(DOXYGEN) $(DOXYFILE)

## Generate a default Doxyfile configuration if none exists
$(DOXYFILE):
	@echo "No $(DOXYFILE) found. Generating initial config..."
	$(DOXYGEN) -g $(DOXYFILE)
	@echo "OUTPUT_DIRECTORY = $(DOC_DIR)" >> $(DOXYFILE)
	@echo "GENERATE_HTML    = YES" >> $(DOXYFILE)
	@echo "GENERATE_LATEX   = NO" >> $(DOXYFILE)

## Initialize/generate Doxyfile explicitly without building
docs-init: $(DOXYFILE)

## Remove generated documentation build outputs
docs-clean:
	@echo "Cleaning documentation artifacts..."
	rm -rf $(DOC_DIR)/html $(DOC_DIR)/latex html latex

## Open generated HTML documentation in the default system browser
docs-view: docs
	@if [ -f "$(DOC_DIR)/html/index.html" ]; then \
		open "$(DOC_DIR)/html/index.html" 2>/dev/null || \
		xdg-open "$(DOC_DIR)/html/index.html" 2>/dev/null || \
		start "$(DOC_DIR)/html/index.html" 2>/dev/null; \
	elif [ -f "html/index.html" ]; then \
		open "html/index.html" 2>/dev/null || \
		xdg-open "html/index.html" 2>/dev/null || \
		start "html/index.html" 2>/dev/null; \
	else \
		echo "Error: HTML documentation not found. Run 'make docs' first."; \
	fi

# Default settings (can be overridden from CLI)
ELF ?= $(BUILD_TYPE)/device.elf
ADDR2LINE ?= ~/eclipse/eclipse/arduinoPlugin/packages/esp32/tools/xtensa-esp32-elf-gcc/esp-2021r2-patch5-8.4.0/bin/xtensa-esp32-elf-addr2line

.PHONY: decode
decode:
ifndef BT
	$(error BT is not set. Usage: make decode BT="0x400d6331 0x400d640f ...")
endif
	@if [ ! -f $(ELF) ]; then \
		echo "Error: ELF file '$(ELF)' not found. Specify via ELF=path/to/file.elf"; \
		exit 1; \
	fi
	$(ADDR2LINE) -pfiaC -e $(ELF) $(BT)
