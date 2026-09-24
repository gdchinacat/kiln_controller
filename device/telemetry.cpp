
#include <Esp.h>
#include <WiFiClientSecure.h>
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
       int httpCode = http.POST(NULL, 0);  // todo actually send data
       String content = http.getString();
       http.end();
       if (httpCode == 200 || httpCode == 201) {
               log_d("sent telemetry");
               return true;
       } else if (httpCode == 404) {
               log_e("Device does not exist (404). Initiating registration.");
               registration.reset();
               reboot = true;
       } else {
               log_e("error sending telemetry: %d %s", httpCode, content.c_str());
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
