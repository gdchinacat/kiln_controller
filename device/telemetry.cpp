
#include <Arduino.h>
#include <stdint.h>
#include <cstring>
#include <string.h>
#include <Esp.h>
#include <WebSocketsClient.h>
#include <WiFiClientSecure.h>
#include "firing.h"
#include "protocol.h"
#include "registrar.h"
#include "registration.h"
#include "telemetry.h"
#include "time_sync.h"

extern Registration registration;
extern Firing firing;
extern TimeSync timeSync;
extern bool reboot;
extern const char * caCert;

enum class _UrlParseState {
	PROTO,
	HOST,
	PORT,
	DONE
};

class _Url {
public:
	const char* host;
	uint16_t port;
	const char* path = NULL;
	const char* protocol;

	_Url(const char* url) {
		_UrlParseState state = _UrlParseState::PROTO;
		const char* start = url;
		for (const char* c = start; *c != NULL && state != _UrlParseState::DONE; c++) {
			switch (state) {
				case _UrlParseState::PROTO:
					if (*c == ':') {
						protocol = _string(start, c - start);
						c += 2; // skip ":/" to "/", loop wil advance to host
						start = c + 1;
						state = _UrlParseState::HOST;
					}
					break;
				case _UrlParseState::HOST:
					if (*c == ':' or *c == '/') {
						host = _string(start, c - start);
						if (*c == '/') {
							port = (protocol == "https") ? 443 : 80;
							start = c;
							path = start;
							state = _UrlParseState::DONE;
						} else {
							start = c + 1;
							state = _UrlParseState::PORT;
						}
					}
					break;
				case _UrlParseState::PORT:
					if (*c == '/') {
						if (c - start) {
							port = atoi(_string(start, c - start));
						} else {
							port = (protocol == "https") ? 443 : 80;
						}
						start = c;
						path = start;
						state = _UrlParseState::DONE;
					}
					break;
			}
		}
	}

private:
	const char * _string(const char* s, size_t len) {
		char* copy = new char[len + 1];
		copy[len] = 0;
		strncpy(copy, s, len);
		return copy;
	}
};

void Telemetry::setupWebSocket() {
	wifi.setCACert(caCert);
	url = registration.service.url;
	url += "telemetry";

	_Url _url(url.c_str());

    webSocket.beginSslWithCA(_url.host, _url.port, _url.path, caCert, _url.protocol);
    String authentication("Bearer ");
    authentication += registration.service.auth_token;
	webSocket.setAuthorization(authentication.c_str());
	webSocket.setReconnectInterval(TELEMETRY_WS_RECONNECT_INTERVAL);
	webSocket.onEvent(
		[this] (WStype_t type, uint8_t * payload, size_t length)
		{
			this->webSocketEvent(type, payload, length);
		}
	);

	log_i("telemetry URL is %s", webSocket.getUrl().c_str());
	send();
}

bool Telemetry::send() {

	// todo - check the status of wifi and don't even try to send if wifi isn't
	//        connected.

	// Get the sample buffers to send
	uint16_t sampleCount = 0;
	SampleBuffer sampleBuffers[2]{};
	for (int i = 0; i < 2; i++) {
		SampleBuffer* buffer = &sampleBuffers[i];
		sampler.getSamples(i, buffer);
		if (!buffer->count) {
			break;
		}
		sampleCount += buffer->count;
	}

	protocol::Telemetry _telemetry = {
		.timestamp = timeSync.now(),
		.state = firing.currentState(),
		.sample_count = sampleCount
	};


	// todo check the success/failure for the sends below
	bool success = webSocket._sendFrame(
			WSop_binary,
			(uint8_t*) &_telemetry,
			sizeof(protocol::Telemetry),
			sampleCount == 0);
	uint16_t _sampleCount = sampleCount;
	for (int i = 0; i < 2 ; i++) {
		SampleBuffer buffer = sampleBuffers[i];
		if (buffer.count) {
			_sampleCount -= buffer.count;
			success = webSocket._sendFrame(
				WSop_continuation ,
				(uint8_t*)buffer.buffer,
				buffer.count * sizeof(protocol::Sample),
				_sampleCount == 0);
			if (success) {
				// todo discard samples through command to confirm they were received.
				//      maybe do it by timestamp rather than count.
				sampler.discard(sampleCount);
				log_v("sent %d samples", sampleCount);
			}
		}
	}

	return false;
}

void Telemetry::setup() {
	setupWebSocket();
	sampler.setup();
}

void Telemetry::loop() {
	webSocket.loop();
	sampler.loop();
	sender.loop();
}

void Telemetry::dispatchCommand(uint8_t* payload, size_t length) {
	if (length < sizeof(protocol::Command)) {
		log_e("received invalid command length %d", length);
		//todo: give the reliability of TCP/IP/SSL, etc this is most likely a
		//      version sync issue between client and server. Handling is
		//      deferred till versioning is implemented.
		webSocket.disconnect();
		setupWebSocket();
		return;
	}

	protocol::Command* command = (protocol::Command*)payload;

	switch (static_cast<protocol::CommandType>(command->type)) {
		case protocol::CommandType::SET_TIME:
			timeSync.setTime(static_cast<protocol::SetTimeCommand*>(command));
			break;
		case protocol::CommandType::START:
			firing.start(static_cast<protocol::StartCommand*>(command));
			break;
		case protocol::CommandType::STOP:
			firing.stop(static_cast<protocol::StopCommand*>(command));
			break;
		case protocol::CommandType::PAUSE:
			firing.pause(static_cast<protocol::PauseCommand*>(command));
			break;
		case protocol::CommandType::RESUME:
			firing.resume(static_cast<protocol::ResumeCommand*>(command));
			break;
		default:
			log_d("received unimplemented command %d", command->type);
			break;
	};


}

void Telemetry::webSocketEvent(WStype_t type, uint8_t * payload, size_t length) {

	switch(type) {
		case WStype_DISCONNECTED:
			// todo? WebSocketsClient doesn't seem too expose the status code in
			//       a reasonable way, only through the payload string...is
			//       there a less hacky way to do this?
			if (payload != nullptr && strstr((const char*)payload, "404") != NULL) {
				log_d("Device does not exist on server. Forcing reregistration.");
				registration.reset();
				reboot = true;
			} else {
				log_d("[WSc] Disconnected! reason: %s\n",
						(payload != nullptr ? (const char*)payload : "<unknown>"));
			}
			break;
		case WStype_CONNECTED:
			log_d("[WSc] Connected to url: %s\n", payload);
			break;
		case WStype_TEXT:
			log_d("[WSc] get text: %s\n", payload);
			break;
		case WStype_BIN:
			dispatchCommand(payload, length);
			break;
		case WStype_FRAGMENT_BIN_START:
		case WStype_ERROR:
		case WStype_FRAGMENT_TEXT_START:
		case WStype_FRAGMENT:
		case WStype_FRAGMENT_FIN:
			log_d("[WSc] unhandled %d: %u\n", type, length);
			break;
	}

}
