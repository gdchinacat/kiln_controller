#pragma once

#include <functional>

class Scheduler {
private:
	uint64_t lastCall = 0;
	uint32_t defaultRate;
	uint32_t maxRate;

	/**
	 * @brief Should the callback be called given the current system ticks?
	 */
	bool shouldCall(int64_t ticks);

	const std::function<bool()>callback;

protected:
	uint32_t rate;

	void backoff();
	void resume();

public:
	Scheduler(
			std::function<bool()> cb,
			uint32_t _rate,
			uint32_t _maxRate = 0):
		defaultRate(_rate),
		maxRate(_maxRate ? _maxRate : _rate),
		callback(std::move(cb)),
		rate(_rate)
	{}

    typedef bool (*Callback)();

	void loop();

};
