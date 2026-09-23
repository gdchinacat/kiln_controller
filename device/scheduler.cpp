
#include <Arduino.h>
#include "scheduler.h"

void Scheduler::sent() {
	unsigned int now = millis();
	lastUpdate = (now / sendRate) * sendRate;
}

bool Scheduler::shouldSend() {
	unsigned int now = millis();
	return (lastUpdate == 0 || lastUpdate + sendRate < now);
}

void Scheduler::backOffSends() {
	sendRate = min(sendRate * 2, maxSendRate);
}

void Scheduler::resumeSends() {
	sendRate = defaultSendRate; //resume normal send rate
}

void Scheduler::loop() {
	if (shouldSend()) {
		if (scheduled()) {
			sent();
		}

		// todo include memory in the status payload (to watch for signs of failure)
		log_i("total: %d free: %d  min free: %d max allocation: %d",
				ESP.getHeapSize(),
				ESP.getFreeHeap(),
				ESP.getMinFreeHeap(),
				ESP.getMaxAllocHeap());
	}
}
