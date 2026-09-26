#ifndef TELEMETRY_H
#define TELEMETRY_H

#include <WebSocketsClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>

#include "scheduler.h"
#include "registrar.h"
#include "sampler.h"

#define TELEMETRY_SAMPLE_PERIOD 1000
#define TELEMETRY_SEND_RATE 3000
#define TELEMETRY_WS_RECONNECT_INTERVAL 4000

/**
 * @brief internal subclass of WebSocketsClient to allow sending the frames
 *		necessary (binary/!fin; continuation/!fin; ...; continuation/fin).
 */
class _WebSocketsClient : public WebSocketsClient {
public:
	bool _sendFrame(WSopcode_t opcode, uint8_t* payload, size_t length, bool fin) {
		return sendFrame(&_client, opcode, payload, length, fin);
	}
};

class Telemetry {
private:
	Scheduler sender;
	Sampler sampler;

	String url;
	WiFiClientSecure wifi;
	_WebSocketsClient webSocket;

	void setupWebSocket();

	bool send();


	void webSocketEvent(WStype_t type, uint8_t * payload, size_t length);

public:
	Telemetry():
		sender([this]() {return this->send();},
				TELEMETRY_SEND_RATE, TELEMETRY_SEND_RATE * (1 << 4)),
		sampler(TELEMETRY_SAMPLE_PERIOD)
	{};

	void setup();
	void loop();
};

#endif
