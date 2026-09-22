BUILD_TYPE := Release

# Define your tool paths based on your Eclipse plugin structure
ESPTOOL := python3 /home/lonnieh/eclipse/eclipse/arduinoPlugin/packages/esp32/tools/esptool_py/4.5.1/esptool.py
PARTITION_GEN := /home/lonnieh/eclipse/eclipse/arduinoPlugin/packages/esp32/hardware/esp32/3.3.11/tools/gen_esp32part.py

# Source paths for core layout
PARTITION_CSV  := /home/lonnieh/eclipse/eclipse/arduinoPlugin/packages/esp32/hardware/esp32/3.3.11/tools/partitions/default.csv

.PHONY: device
device:
	# 1. Compile the main-build target to generate the ELF file
	make -C $(BUILD_TYPE) main-build
	
	# 2. Convert the ELF file to an ESP32 image using elf2image
	$(ESPTOOL) --chip esp32 elf2image --flash_mode dio --flash_freq 80m --flash_size 4MB -o $(BUILD_TYPE)/device.bin $(BUILD_TYPE)/device.elf
	
	# Fix name formatting if esptool appended the segment address destination
	@if [ -f "$(BUILD_TYPE)/device.bin0x00000.bin" ]; then \
		mv $(BUILD_TYPE)/device.bin0x00000.bin $(BUILD_TYPE)/device.bin; \
	fi
	
	# 3. Generate the partitions binary from the CSV layout
	python3 $(PARTITION_GEN) -q $(PARTITION_CSV) $(BUILD_TYPE)/device.partitions.bin
	
	# 4. FIX: Deploy your local permanent stable bootloader into position
	@if [ -f "stable_bootloader.bin" ]; then \
		cp stable_bootloader.bin $(BUILD_TYPE)/device.bootloader.bin; \
	else \
		echo "ERROR: stable_bootloader.bin missing from project root folder! Please run Step 1."; \
		exit 1; \
	fi

.PHONY: clean
clean:
	make -C $(BUILD_TYPE) clean
	rm -f $(BUILD_TYPE)/*.bin

.PHONY: upload
upload: device
	$(ESPTOOL) --chip esp32 --port /dev/ttyUSB0 --baud 921600 --before default_reset --after hard_reset write_flash -z --flash_mode dio --flash_freq 80m --flash_size 4MB 0x1000 /home/lonnieh/eclipse-workspace/kiln_controller/device/$(BUILD_TYPE)/device.bootloader.bin 0x8000 /home/lonnieh/eclipse-workspace/kiln_controller/device/$(BUILD_TYPE)/device.partitions.bin 0xe000 /home/lonnieh/eclipse/eclipse/arduinoPlugin/packages/esp32/hardware/esp32/3.3.11/tools/partitions/boot_app0.bin 0x10000 /home/lonnieh/eclipse-workspace/kiln_controller/device/$(BUILD_TYPE)/device.bin

