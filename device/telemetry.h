#ifndef TELEMETRY_H
#define TELEMETRY_H

//todo - HTTPClient does runtime memory allocation that is not suitable for the
//       running loop. Get everything working then replace/configure it to not
//       allocate memory.
#include <HTTPClient.h>
#include <WiFi.h>

#include "registrar.h"

// todo include commands.h

class Telemetry {
private:
	//todo - sample ring buffer
	WiFiClient wifi;
	HTTPClient http;

	void send();
	void setupHTTPClient();

public:
	Telemetry();

	void setup();
	void loop();
};

#endif
