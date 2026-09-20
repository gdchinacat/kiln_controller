
#include "registrar.h"
#include "telemetry.h"

extern Registration registration;
extern bool reboot;

Telemetry::Telemetry() {}

void Telemetry::send() {
	int httpCode = http.POST(NULL, 0);  // todo actually send data
	String content = http.getString();
	if (httpCode == 200 || httpCode == 201) {
		log_d("sent telemetry");
	} else if (httpCode == 404) {
		log_e("Device does not exist (404). Initiating registration.");
		registration.reset();
		reboot = true;
	} else {
		log_e("error sending telemetry: %d %s", httpCode, content.c_str());
	}
}

void Telemetry::setupHTTPClient() {
	String url = registration.service.url;
	url += "telemetry";
	http.useHTTP10(true);
	http.setFollowRedirects(HTTPC_DISABLE_FOLLOW_REDIRECTS);
	http.setAuthorization(registration.service.auth_token);
	http.setAuthorizationType("Bearer");
	http.addHeader("Content-Type", "application/octet_stream");
	http.begin(wifi, url);

	log_i("sending telemetry to %s", url.c_str());
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
