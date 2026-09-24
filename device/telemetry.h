#ifndef TELEMETRY_H
#define TELEMETRY_H

//todo - HTTPClient does runtime memory allocation that is not suitable for the
//       running loop. Get everything working then replace/configure it to not
//       allocate memory.
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>

#include "registrar.h"
#include "sampler.h"
#include "scheduler.h"

#define TELEMETRY_SAMPLE_PERIOD 5000
#define TELEMETRY_SEND_RATE 5000

class Telemetry {
private:
	Scheduler sender;
	Sampler sampler;

	//todo - sample ring buffer
	String url;
	WiFiClientSecure wifi;
	HTTPClient http;

	void setupHTTPClient();

	bool send();

public:
	Telemetry():
		sender([this]() {return this->send();},
				TELEMETRY_SEND_RATE, TELEMETRY_SEND_RATE * (1 << 4)),
		sampler(TELEMETRY_SAMPLE_PERIOD)
	{};

	void setup();
	void loop();
};

#endif
