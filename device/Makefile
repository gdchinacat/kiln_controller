
BUILD_TYPE := Release

.PHONY: all
all:
	make -C $(BUILD_TYPE) main-build

.PHONY: upload
upload: all
	python3 /home/lonnieh/eclipse/eclipse/arduinoPlugin/packages/esp32/tools/esptool_py/4.5.1/esptool.py --chip esp32 --port /dev/ttyUSB0 --baud 921600 --before default_reset --after hard_reset write_flash -z --flash_mode dio --flash_freq 80m --flash_size 4MB 0x1000 /home/lonnieh/eclipse-workspace/kiln_controller/device/$(BUILD_TYPE)/device.bootloader.bin 0x8000 /home/lonnieh/eclipse-workspace/kiln_controller/device/$(BUILD_TYPE)/device.partitions.bin 0xe000 /home/lonnieh/eclipse/eclipse/arduinoPlugin/packages/esp32/hardware/esp32/2.0.17/tools/partitions/boot_app0.bin 0x10000 /home/lonnieh/eclipse-workspace/kiln_controller/device/$(BUILD_TYPE)/device.bin
