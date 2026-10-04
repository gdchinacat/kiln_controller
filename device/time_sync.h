#pragma once

#include <stdint.h>
#include <esp_timer.h>
#include "protocol.h"


/**
 * @brief TimeSync tracks the time delta between the device and service.
 */
class TimeSync {
private:
	/**
	 * @brief the adjustment to synchronize uptime() based time with server
	 *        epoch time.
	 */
	uint64_t offset = 0;

public:
	TimeSync();

	/**
	 * @brief Set the time.
	 */
	void setTime(protocol::SetTimeCommand* command);

	/**
	 * @brief get the uptime in milliseconds.
	 */
	static inline int64_t uptime() { return esp_timer_get_time() / 1000ULL; }

	/**
	 * @brief Get the current synced time in milliseconds, or 0 if time is not
	 * synced.
	 */
	inline uint64_t now(int64_t _uptime = uptime()) { return offset == 0 ? 0 : offset + _uptime; }

};
