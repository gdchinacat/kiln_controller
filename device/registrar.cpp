#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFiClient.h>
#include "registrar.h"
#include "registration.h"

extern Registration registration;
extern bool reboot;

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
"<label>Server Registration URL:</label>""<input type='text' id='url' name='url' value='" REGISTRATION_URL "' required>"
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
	: _apSSID(apSSID), _apIP(192, 168, 4, 1), _server(80) {}

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
	log_i("Registration service started on SSID %s", _apSSID);
}

void Registrar::handleRoot() {
	log_i("handleRoot %s", _server.uri().c_str());
	_server.send(200, "text/html", INDEX_HTML);
}

void Registrar::handleScan() {
	log_d("handleScan");

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
	log_d("handleSubmit");
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
			bool registered = registerWithService(_name, _username, _password);
			if (registered) {
				registration.save();
				reboot = true;
				return;
			}
		} else {
			log_e("cound not connect to %s", registration.wifi.ssid);
		}
		start();
	} else {
		_server.send(400, "text/plain", "Error: Missing configuration fields.");
	}
}

void Registrar::loop() {
	_dnsServer.processNextRequest();
	_server.handleClient();
}

bool Registrar::registerWithService(String name, String username, String password) {
	WiFiClient wifi;
	HTTPClient http;
	http.begin(wifi, registration.service.url);
	http.setAuthorization(username.c_str(), password.c_str());
	log_i("posting to %s", registration.service.url);
	http.addHeader("Content-Type", "application/json");

	String payload = "{\"name\":\"" + name + "\"}";

	int httpCode = http.POST(payload);
	String content = http.getString();
	http.end();
	
	if (httpCode == 200 || httpCode == 201) {
		JsonDocument json;
		DeserializationError error = deserializeJson(json, content);
		if (error) {
			log_e("deserializeJson() failed: %s", error.f_str());
		}

		if (not json["id"].is<unsigned int>()
			|| (not json["auth_token"].is<String>())) {
			log_e("received bad registration response: %s", content.c_str());
			return false;
		}
		unsigned int id = json["id"];
		const char* auth_token = json["auth_token"];

		snprintf(registration.service.url, sizeof(registration.service.url),
			 	 "%s%d/", registration.service.url, id);
		strncpy(registration.service.auth_token, auth_token, sizeof(registration.service.auth_token));

		log_d("registration updated to url %s, auth token \"%s\"", registration.service.url, registration.service.auth_token);
		return true;
	} else {
		log_e("registration failed with %d: %s", httpCode, content.c_str()); 
		return false;
	}
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
