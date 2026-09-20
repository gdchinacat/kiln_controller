#include "registrar.h"
#include "telemetry.h"

Registrar registrar;
Telemetry telemetry;

enum DeviceState { REGISTERING, RUNNING };
DeviceState currentState;

void setup() {
	Serial.begin(921600);
	delay(1000); // Settling delay for stable serial output

	if (registrar.load()) {
		registrar.registration.wifi.connect();
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
	switch (currentState) {
		case REGISTERING:
			registrar.loop();
			break;

		case RUNNING:
			telemetry.loop();
			break;
	}
}

