#ifndef REGISTRAR_H
#define REGISTRAR_H

#include <WiFi.h>
#include <DNSServer.h>
#include <WebServer.h>
#include "registration.h"

#define REGISTRATION_AP "Kiln Registration"
#define REGISTRATION_URL "http://dupree:5000/device/"


class Registrar {
private:
	const char* _apSSID;
	const byte DNS_PORT = 53;
	IPAddress _apIP;

	DNSServer _dnsServer;
	WebServer _server;

	// Route Handlers
	void handleRoot();
	void handleScan();
	void handleSubmit();

	bool registerWithService(String name, String username, String password);

public:
	Registrar(const char* apSSID = REGISTRATION_AP);

	void start();
	void loop();
};

#endif
