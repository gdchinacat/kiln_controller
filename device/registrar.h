#ifndef REGISTRAR_H
#define REGISTRAR_H

#include <DNSServer.h>
#include <IPAddress.h>
#include <WebServer.h>
#include "registration.h"

#define REGISTRATION_URL "https://dupree:5000/device/"
#define REGISTRATION_AP_SSID "Kiln Registration"
#define REGISTRATION_AP_IP (IPAddress(192, 168, 4, 1))

class Registrar {
private:
	DNSServer _dnsServer;
	WebServer _server;

	// Route Handlers
	void handleRoot();
	void handleScan();
	void handleSubmit();

	bool registerWithService(String name, String username, String password);

public:
	void start();
	void loop();
};

#endif
