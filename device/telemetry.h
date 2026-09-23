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

class Telemetry : public Scheduler {
private:

	//todo - sample ring buffer
	String url;
	WiFiClientSecure wifi;
	HTTPClient http;

	void setupHTTPClient();

protected:
	bool scheduled();

public:
	void setup();
};

#endif
