#ifndef REGISTRATION_H
#define REGISTRATION_H

#include <Preferences.h>
#include <WiFi.h>

#define REGISTRATION_VERSION 1
#define REGISTRATION_PREFS_NS "registration"
#define REGISTRATION_PREFS_KEY "bytes"

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
	Registration();
	char version;
	Wifi wifi;
	Service service;

	bool load();
	bool save();
	bool reset();

private:
	Preferences _prefs;
};

#endif
