
#include <Arduino.h>
#include "firing.h"
#include "protocol.h"
#include "sampler.h"

extern Firing firing;
extern Sampler sampler;

Firing::Firing() {

}

void Firing::setState(State state) {
	sampler.currentSample()->device_state |= static_cast<uint16_t>(firing.currentState());
	log_i("firing state changed to %s", str(state));
}

void Firing::start(protocol::StartCommand* command) {
	log_i("starting");
}

void Firing::stop(protocol::StopCommand* command) {
	log_i("stopping");
}

void Firing::pause(protocol::PauseCommand* command) {
	log_i("pausing");
}

void Firing::resume(protocol::ResumeCommand* command) {
	log_i("resuming");
}
