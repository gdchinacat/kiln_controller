
#include <Arduino.h>
#include "firing.h"
#include "protocol.h"


Firing::Firing() {

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
