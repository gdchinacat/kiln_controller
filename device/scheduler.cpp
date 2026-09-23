
#include <Arduino.h>
#include "scheduler.h"

bool Scheduler::shouldCall(unsigned int now) {
	return (lastCall == 0 || lastCall + rate < now);
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
		lastCall = (now / rate) * rate;
		log_e("[%d] lastCall=%d", now, lastCall);

		// todo include memory in the status payload (to watch for signs of failure)
		log_i("total: %d free: %d  min free: %d max allocation: %d",
				ESP.getHeapSize(),
				ESP.getFreeHeap(),
				ESP.getMinFreeHeap(),
				ESP.getMaxAllocHeap());
	}
}
