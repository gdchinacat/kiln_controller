#ifndef SCHEDULER_H
#define SCHEDULER_H

#include <functional>

class Scheduler {
private:
	unsigned int lastCall = 0;
	unsigned int defaultRate;
	unsigned int maxRate;

	bool shouldCall(unsigned int now);

	const std::function<bool()>callback;

protected:
	unsigned int rate;

	void backoff();
	void resume();

public:
	Scheduler(
			std::function<bool()> cb,
			unsigned int _rate,
			unsigned int _maxRate = 0):
		defaultRate(_rate),
		maxRate(_maxRate ? _maxRate : _rate),
		callback(std::move(cb)),
		rate(_rate)
	{}

    typedef bool (*Callback)();

	void loop();

};

#endif
