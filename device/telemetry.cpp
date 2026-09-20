
#include "registrar.h"
#include "telemetry.h"

extern Registrar registrar;

Telemetry::Telemetry() {}

void Telemetry::send() {
	log_d("sending telemetry");
}

void Telemetry::setupHTTPClient() {
	http.begin(wifi, registrar.registration.service.url);
	http.setAuthorization(registrar.registration.service.auth_token);
	http.setAuthorizationType("Bearer");
	http.addHeader("Content-Type", "application/octet_stream");
}

void Telemetry::setup() {
	setupHTTPClient();
}
	
void Telemetry::loop() {
	static unsigned long lastUpdate = 0;
	unsigned long now = millis();
	if (now - lastUpdate > 5000) {
		send();
		if (lastUpdate == 0 ) {
			lastUpdate = now;
		} else {
			lastUpdate += 5000;
		}
	}
}
