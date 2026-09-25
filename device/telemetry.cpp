
#include <stdint.h>
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
	http.setFollowRedirects(HTTPC_DISABLE_FOLLOW_REDIRECTS);
	http.setAuthorization(registration.service.auth_token);
	http.setAuthorizationType("Bearer");
	http.setTimeout(30000);
	http.addHeader("Content-Type", "application/octet_stream");

	log_i("telemetry URL is %s", url.c_str());
}

bool Telemetry::send() {
	   http.begin(wifi, url);

	   protocol::Telemetry telemetry {
		   .timestamp = sampler.now(),
		   .state = protocol::State::IDLE,
		   .sample_count = 0
	   };

	   int httpCode = http.POST((uint8_t*)&telemetry, sizeof(telemetry));
	   int size = http.getSize();
	   uint64_t buffer[1];
	   http.getStream().read((uint8_t*)buffer, sizeof(buffer));
	   http.end();
	   if (httpCode == 200 || httpCode == 201) {
		   sampler.set_now(buffer[0]);

		   log_d("sent telemetry");
		   return true;
	   //} else if (httpCode == 404) { todo - handle other http codes like NOT_AUTH...
	   } else if (httpCode == 404) {
			   log_e("Device does not exist (404). Initiating registration.");
			   registration.reset();
			   reboot = true;
	   } else {
			   log_e("error sending telemetry: %d", httpCode);
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
