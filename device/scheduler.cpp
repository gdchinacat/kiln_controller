
#include <Arduino.h>
#include "scheduler.h"

bool Scheduler::shouldCall(unsigned int now) {
	return lastCall + rate < now;
}

void Scheduler::backoff() {
	rate = min(rate * 2, maxRate);
}

void Scheduler::resume() {
	rate = defaultRate; //resume normal rate
}


void Scheduler::loop() {
	unsigned int now = millis();
	if (shouldCall(now)) {
		callback();
		lastCall = now - now % rate;
	}
}
