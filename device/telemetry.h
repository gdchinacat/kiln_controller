#ifndef TELEMETRY_H
#define TELEMETRY_H

//todo - HTTPClient does runtime memory allocation that is not suitable for the
//       running loop. Get everything working then replace/configure it to not
//       allocate memory.
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>

#include "registrar.h"
#include "scheduler.h"

// todo include commands.h
#define TELEMETRY_SEND_RATE 5000

class Telemetry {
private:
	Scheduler sender;

	//todo - sample ring buffer
	String url;
	WiFiClientSecure wifi;
	HTTPClient http;

	void setupHTTPClient();

	bool send();

public:
	Telemetry():
		sender([this]() {return this->send();},
				TELEMETRY_SEND_RATE, TELEMETRY_SEND_RATE * (1 << 4))
	{};

	void setup();
	void loop();
};

#endif
