#include "registration.h"
#include <WiFiClient.h>

extern bool reboot;

Registration::Registration() : version(REGISTRATION_VERSION) {}

bool Registration::load() {
	_prefs.begin(REGISTRATION_PREFS_NS, true);
	bool valid = false;
	size_t size = _prefs.getBytes(REGISTRATION_PREFS_KEY, this, sizeof(Registration));
	_prefs.end();
	if ((size == sizeof(Registration))
		&& (version == REGISTRATION_VERSION)) {
		// todo add upgrade path that doesn't force needless registration
		valid = true;
		log_i("found valid registration");
	} else {
		if (REGISTRATION_VERSION != -1 && size != 0) {
			log_e("existing registration size %d (should be %d) version %d (should be %d)",
				size, sizeof(Registration), version, REGISTRATION_VERSION);
			reset();
		}
	}
	return valid;
}

bool Registration::save() {
	_prefs.begin(REGISTRATION_PREFS_NS, false);
	bool success = _prefs.putBytes(REGISTRATION_PREFS_KEY, this, sizeof(Registration));
	_prefs.end();
	if (not success) {
		log_e("failed to save registration");
	} else {
		log_i("saved registration");
	}
	return success;
}

bool Registration::reset() {
	_prefs.begin(REGISTRATION_PREFS_NS, false);
	bool success = _prefs.clear();
	_prefs.end();
	if (not success) {
		log_e("failed to reset registration");
	} else {
		log_i("reset registration");
	}
	return success;
}

bool Wifi::connect() {
	log_d("Connecting to SSID %s", ssid);

	WiFi.mode(WIFI_STA);
	WiFi.begin(ssid, password);

	int timeout = 0;
	while (WiFi.status() != WL_CONNECTED && timeout < 30) {
		delay(500);
		timeout++;
	}

	if (WiFi.status() != WL_CONNECTED) {
		log_e("Connection timeout or bad credentials: %d", WiFi.status());
		return false;
	}

	log_i("Connected to %s", ssid);
	return true;
}
