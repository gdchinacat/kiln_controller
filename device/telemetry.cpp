
#include <stdint.h>
#include <cstring>
#include <Esp.h>
#include <WiFiClientSecure.h>
#include "protocol.h"
#include "registrar.h"
#include "registration.h"
#include "telemetry.h"

extern Registration registration;
extern bool reboot;
extern const char * caCert;

void Telemetry::setupHTTPClient() {
	wifi.setCACert(caCert);
	url = registration.service.url;
	url += "telemetry";
	http.begin(wifi, url);
	http.setReuse(true);
	http.setFollowRedirects(HTTPC_DISABLE_FOLLOW_REDIRECTS);
	http.setAuthorization(registration.service.auth_token);
	http.setAuthorizationType("Bearer");
	http.setTimeout(30000);
	http.addHeader("Content-Type", "application/octet_stream");

	log_i("telemetry URL is %s", url.c_str());
}

bool Telemetry::send() {

	// todo - check the status of wifi and don't even try to send if wifi isn't
	//        connected.
	uint8_t buffer[1024]; // both request and response buffer

	protocol::Telemetry* telemetry = (protocol::Telemetry*)buffer;
	protocol::Sample* sample = (protocol::Sample*)(telemetry + 1);
	telemetry->timestamp = sampler.now();
	telemetry->state = protocol::State::IDLE;
	telemetry->sample_count = 0;

	memcpy(sample, sampler.currentSample(), sizeof(protocol::Sample));
	telemetry->sample_count += 1;
	sample += 1;

	size_t size = (uint8_t*)sample - buffer;
	log_e("writing telemetry with %d samples, (%d bytes)", telemetry->sample_count, size);
	int httpCode = http.POST(buffer, size);
	size = http.getSize();
	http.getStream().read((uint8_t*)buffer, sizeof(buffer));
	if (httpCode == 200 || httpCode == 201) {
		sampler.set_now(((protocol::TelemetryResponse*)buffer)->timestamp);

		log_d("sent telemetry");
		return true;
	   //} else if (httpCode == 404) { todo - handle other http codes like NOT_AUTH...
	} else if (httpCode == 404) {
		log_e("Device does not exist (404). Initiating registration.");
		registration.reset();
		reboot = true;
	} else {
		// todo - it is a bit heavy handed to reset the client on any other
		//        error, but it's the safe thing...look at statuses and other
		//        things httpclient exposes and improve this to realy be for
		//        network errors.
		log_e("error sending telemetry: %d", httpCode);
		http.end();
		setupHTTPClient();
	}
	return false;
}

void Telemetry::setup() {
	setupHTTPClient();
	sampler.setup();
}
	
void Telemetry::loop() {
	sampler.loop();
	sender.loop();
}
