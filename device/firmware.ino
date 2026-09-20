#include "registrar.h"
#include "telemetry.h"

Registration registration;
Registrar registrar;
Telemetry telemetry;
bool reboot = false;

enum DeviceState { REGISTERING, RUNNING };
DeviceState currentState;

void setup() {
	Serial.begin(921600);
	delay(1000); // Settling delay for stable serial output

	if (registration.load()) {
		registration.wifi.connect();
		//todo set up the device (pins, interupts, etc)
		telemetry.setup();

		currentState = RUNNING;
	} else {
		Serial.println("No valid configuration found. Starting registration.");
		registrar.start();

		currentState = REGISTERING;
	}
}

void loop() {
	if (reboot) {
		log_i("Rebooting device ...");
		delay(2000);
		ESP.restart();
	}

	switch (currentState) {
		case REGISTERING:
			registrar.loop();
			break;

		case RUNNING:
			telemetry.loop();
			break;
	}
}

