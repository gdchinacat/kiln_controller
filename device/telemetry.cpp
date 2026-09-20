
#include "registrar.h"
#include "telemetry.h"

extern Registrar registrar;

Telemetry::Telemetry() {}

void Telemetry::send() {
	int httpCode = http.POST(NULL, 0);  // todo actually send data
	String content = http.getString();
	if (httpCode == 200 || httpCode == 201) {
		log_d("sent telemetry");
	} else {
		log_e("error sending telemetry: %d %s", httpCode, content);
	}
}

void Telemetry::setupHTTPClient() {
	String url = registrar.registration.service.url;
	url += "telemetry";
	http.begin(wifi, url);
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
