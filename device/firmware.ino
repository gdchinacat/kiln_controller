#include "registrar.h"

Registrar registrar("KilnRegistration");

enum DeviceState { REGISTERING, RUNNING };
DeviceState currentState;

void setup() {
	Serial.begin(115200);
	delay(1000); // Settling delay for stable serial output

	if (registrar.load()) {
		registrar.registration.wifi.connect();
		currentState = RUNNING;
	} else {
		Serial.println("No valid configuration found. Launching registration Mode.");
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
			runningLoop();
			break;
	}
}

// todo move telemetry stuff into telemetry.(h|cpp)
void sendTelemetry() {
	// todo send the telemetry to service
}

void telemetryLoop() {
	static unsigned long lastUpdate = 0;
	unsigned long now = millis();
	if (now - lastUpdate > 5000) {
		sendTelemetry();
		if (lastUpdate == 0 ) {
			lastUpdate = now;
		} else {
			lastUpdate += 5000;
		}
	}
}

void runningLoop() {
	telemetryLoop();
}
