#ifndef SCHEDULER_H
#define SCHEDULER_H

#define TELEMETRY_SEND_RATE 1000

class Scheduler {
private:
	unsigned int lastUpdate = 0;
	unsigned int defaultSendRate = TELEMETRY_SEND_RATE;
	unsigned int maxSendRate = TELEMETRY_SEND_RATE * (1 << 4);

	bool shouldSend();
	void sent();

protected:
	unsigned int sendRate = TELEMETRY_SEND_RATE;
	virtual bool scheduled();

	void backOffSends();
	void resumeSends();

public:
	void loop();
};
#endif
