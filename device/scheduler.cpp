
#include <Arduino.h>
#include "scheduler.h"
#include "time_sync.h"

bool Scheduler::shouldCall(int64_t ticks) {
	return lastCall + rate < ticks;
}

void Scheduler::backoff() {
	rate = min(rate * 2, maxRate);
}

void Scheduler::resume() {
	rate = defaultRate; //resume normal rate
}


void Scheduler::loop() {
	int64_t now = TimeSync::uptime();
	if (shouldCall(now)) {
		callback();
		lastCall = now - now % rate;
	}
}
