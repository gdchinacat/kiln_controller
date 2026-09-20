#include <ArduinoJson.h>
#include <WiFiClient.h>
#include "registrar.h"


#define REGISTRATION_PREFS_NS "registration"
#define REGISTRATION_PREFS_KEY "bytes"

const char INDEX_HTML[] PROGMEM =
"<!DOCTYPE html><html><head>"
"<meta name='viewport' content='width=device-width, initial-scale=1'>"
"<style>body{font-family:Arial,sans-serif;margin:20px;padding:10px;background:#f4f4f9;color:#333;}"
".card{background:white;padding:25px;border-radius:8px;box-shadow:0 4px 6px rgba(0,0,0,0.1);max-width:400px;margin:auto;}"
"select,input[type=text],input[type=password]{width:100%;padding:12px;margin:8px 0 20px 0;box-sizing:border-box;border:1px solid #ccc;border-radius:4px;background:white;}"
"input[type=submit]{width:100%;background-color:#007AFF;color:white;padding:14px;border:none;border-radius:4px;font-size:16px;cursor:pointer;font-weight:bold;}"
"h2{margin-top:0;color:#111;text-align:center;}.status{font-size:13px;color:#666;font-style:italic;margin-top:-10px;margin-bottom:15px;}</style>"
"</head><body><div class='card'>"
"<h2>Kiln Registration</h2>"
"<form action='/submit' method='POST'>"
"<label>Select Wi-Fi Network:</label>"
"<select id='ssid' name='ssid' required>"
"<option value='' disabled selected>Scanning for networks...</option>"
"</select>"
"<div id='scan-status' class='status'>Looking for nearby routers...</div>"
"<label>Wi-Fi Password:</label><input type='password' name='wifi_password'>"
"<label>Server Registration URL:</label><input type='text' id='url' name='url' value='https://host/device/' required>"
"<label>Server username:</label><input type='text' id='username' name='username' value='admin' required>"
"<label>Server password:</label><input type='password' id='password' name='password' value='admin' required>"
"<label>Device Name:</label><input type='text' id='name' name='name' value='' required>"
"<input type='submit' value='Save & Activate Device'>"
"</form></div>"
"<script>"
"window.addEventListener('DOMContentLoaded', () => {"
"  fetch('/scan')"
"	.then(response => response.json())"
"	.then(data => {"
"	  const select = document.getElementById('ssid');"
"	  const status = document.getElementById('scan-status');"
"	  select.innerHTML = '';"
"	  if (data.networks.length === 0) {"
"		select.innerHTML = '<option value=\"\">No networks found</option>';"
"		status.innerText = 'Scan finished. No routers visible.';"
"	  } else {"
"		select.innerHTML = '<option value=\"\" disabled selected>Choose a network...</option>';"
"		data.networks.forEach(net => {"
"		  const opt = document.createElement('option');"
"		  opt.value = net.ssid;"
"		  opt.innerText = `${net.ssid} (${net.rssi} dBm)`;"
"		  select.appendChild(opt);"
"		});"
"		status.innerText = `Scan finished. Found ${data.networks.length} networks.`;"
"	  }"
"	})"
"	.catch(err => {"
"	  document.getElementById('scan-status').innerText = 'Failed to load network list.';"
"	});"
"});"
"</script></body></html>";

Registrar::Registrar(const char* apSSID)
	: _apSSID(apSSID), _apIP(192, 168, 4, 1), _server(80), _reboot(false) {}

bool Registrar::load() {
	_prefs.begin(REGISTRATION_PREFS_NS, true);
	bool valid = _prefs.isKey("bytes");
	if (valid) {
		_prefs.getBytes(REGISTRATION_PREFS_KEY, &registration, sizeof(registration));
	}
	_prefs.end();
	return valid;
}

void Registrar::start() {
	WiFi.mode(WIFI_AP);
	WiFi.softAPConfig(_apIP, _apIP, IPAddress(255, 255, 255, 0));
	WiFi.softAP(_apSSID);

	_dnsServer.start(DNS_PORT, "*", _apIP);

	// Core routes mapping
	_server.on("/", [this]() { this->handleRoot(); });
	_server.on("/scan", [this]() { this->handleScan(); });
	_server.on("/submit", HTTP_POST, [this]() { this->handleSubmit(); });
	_server.onNotFound([this]() { this->handleRoot(); });

	_server.begin();
	Serial.print("[Registrar] Registration service started on SSID ");
	Serial.println(_apSSID);
}

void Registrar::handleRoot() {
	Serial.println("[Registrar] handleRoot");
	_server.send(200, "text/html", INDEX_HTML);
}

void Registrar::handleScan() {
	Serial.println("[Registrar] handleScan");

	int networkCount = WiFi.scanNetworks(false, true);

	JsonDocument doc;
	JsonArray networksArray = doc["networks"].to<JsonArray>();

	for (int i = 0; i < networkCount; ++i) {
		String currentSSID = WiFi.SSID(i);
		int32_t rssi = WiFi.RSSI(i);

		if (currentSSID.length() == 0) continue;

		JsonObject networkObj = networksArray.add<JsonObject>();
		networkObj["ssid"] = currentSSID;
		networkObj["rssi"] = rssi;
	}

	String jsonOutput;
	serializeJson(doc, jsonOutput);
	WiFi.scanDelete();

	// Dispatch application data explicitly as application/json headers
	_server.send(200, "application/json", jsonOutput);
}

void Registrar::handleSubmit() {
	Serial.println("[Registrar] handleSubmit");
	if (_server.hasArg("ssid")
		&& _server.hasArg("wifi_password")
		&& _server.hasArg("url")
		&& _server.hasArg("username")
		&& _server.hasArg("password")
		&& _server.hasArg("name")
	) {
		String _ssid = _server.arg("ssid");
		String _wifi_password = _server.arg("wifi_password");
		String _url = _server.arg("url");
		String _username = _server.arg("username");
		String _password = _server.arg("password");
		String _name = _server.arg("name");

		String response = "<html><body style='font-family:Arial;text-align:center;margin-top:50px;'>"
						  "<h2>Registration received.</h2>"
						  "<p>Device is rebooting.<p>"
						  "</body></html>";
		_server.send(200, "text/html", response);

		_ssid.toCharArray(registration.wifi.ssid, sizeof(registration.wifi.ssid));
		_wifi_password.toCharArray(registration.wifi.password, sizeof(registration.wifi.password));
		_url.toCharArray(registration.service.url, sizeof(registration.service.url));

		if (registration.wifi.connect()) {
			String auth_token = registerWithService(_name, _username, _password);
			if (auth_token != NULL) {
				String _auth_token = String("Bearer ");
				_auth_token += auth_token;
				_auth_token.toCharArray(registration.service.auth_token, sizeof(registration.service.auth_token));
				_prefs.begin(REGISTRATION_PREFS_NS, false);
				_prefs.putBytes(REGISTRATION_PREFS_KEY, &registration, sizeof(registration));
				_prefs.end();
				_reboot = true;
				return;
			} else {
				Serial.println("[Registrar] failed to get auth_token.");
			}
		} else {
			Serial.print("[Registrar] could not connect to ");
			Serial.println(registration.wifi.ssid);
		}
		start();
	} else {
		_server.send(400, "text/plain", "Error: Missing configuration fields.");
	}
}

void Registrar::loop() {
	_dnsServer.processNextRequest();
	_server.handleClient();

	if (_reboot) {
		Serial.println("[Registrar] Rebooting device ...");
		delay(2000);
		ESP.restart();
	}
}

const char* Registrar::registerWithService(String name, String username, String password) {
	WiFiClient wifi;
	HTTPClient http;
	http.begin(wifi, registration.service.url);
	http.setAuthorization(username.c_str(), password.c_str());
	Serial.print("[Registrar] posting to ");
	Serial.println(registration.service.url);
	http.addHeader("Content-Type", "application/json");

	String payload = "{\"name\":\"" + name + "\"}";

	int httpCode = http.POST(payload);
	String content = http.getString();
	http.end();
	
	if (httpCode == 200 || httpCode == 201) {
		JsonDocument json;
		DeserializationError error = deserializeJson(json, content);
		if (error) {
			Serial.print("[Registrar] deserializeJson() failed: ");
			Serial.println(error.f_str());
		}
		const char* auth_token = json["auth_token"];
		Serial.print("[Registrar] got auth_token ");
		Serial.println(auth_token);
		return auth_token;
	} else {
		Serial.print("[Registrar] registration failed: HTTP ");
		Serial.print(httpCode);
		Serial.print(": ");
		Serial.print(content);
		return NULL;
	}
}

void Registrar::reset() {
	_prefs.begin(REGISTRATION_PREFS_NS, false);
	_prefs.clear();
	_prefs.end();
	_reboot = true;
}

bool Wifi::connect() {
	Serial.print("[Wifi] Connecting to ");
	Serial.println(ssid);

	WiFi.mode(WIFI_STA);
	WiFi.begin(ssid, password);

	int timeout = 0;
	while (WiFi.status() != WL_CONNECTED && timeout < 30) {
		delay(500);
		Serial.print(".");
		timeout++;
	}

	if (WiFi.status() != WL_CONNECTED) {
		Serial.print("\n[Wifi] Connection timeout or bad credentials: ");
		Serial.print(WiFi.status());
		return false;
	}

	Serial.print("\n[Wifi] Connected to ");
	Serial.println(ssid);
	return true;
}
