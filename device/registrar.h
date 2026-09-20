#ifndef WIFI_PROVISIONER_H
#define WIFI_PROVISIONER_H

#include <WiFi.h>
#include <DNSServer.h>
#include <WebServer.h>
#include <Preferences.h>
#include <HTTPClient.h>

#define SSID_MAX_LENGTH 33
#define WIFI_PASSWORD_MAX_LENGTH 64
#define URL_MAX_LENGTH 256
#define AUTH_TOKEN_MAX_LENGTH (44 + 8)

class Wifi {
public:
	char ssid[SSID_MAX_LENGTH];
	char password[WIFI_PASSWORD_MAX_LENGTH];
	bool connect();
};

class Service {
public:
	char url[URL_MAX_LENGTH];
	char auth_token[AUTH_TOKEN_MAX_LENGTH];
};

class Registration {
public:
	Wifi wifi;
	Service service;
};


class Registrar {
private:
	const char* _apSSID;
	const byte DNS_PORT = 53;
	IPAddress _apIP;

	DNSServer _dnsServer;
	WebServer _server;
	Preferences _prefs;

	bool _reboot;

	// Route Handlers
	void handleRoot();
	void handleScan();
	void handleSubmit();

	const char* registerWithService(String name, String username, String password);  // returns auth_token

public:
	Registrar(const char* apSSID = "KilnRegistration");

	Registration registration;

	bool load();
	void start();
	void reset();
	void loop();
};

#endif
