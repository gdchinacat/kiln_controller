#pragma once

#include <stdint.h>
#include "protocol.h"

/**
 * @brief TimeSync tracks the time delta between the device and service.
 */
class TimeSync {
private:
	/**
	 * @brief the adjustment to synchronize millis() based time with server
	 *        epoch time.
	 *
	 * This is made more complicated by the fact that epoch time in milliseconds
	 * requires more than 32 bits. Doing everything in seconds results in very
	 * poor resolution and can lead to device being one second ahead or one
	 * second behind actual unix time. A two second slop in a five second
	 * sample period is "too much".
	 *
	 * todo? - is there a way that makes sense (not too convoluted) to use 32
	 *         bit values to accomplish this?
	 */
	uint64_t offset = 0;

public:
	TimeSync();

	/**
	 * @brief Set the time.
	 */
	void setTime(protocol::SetTimeCommand* command);

	/**
	 * @brief Get the current synced time in milliseconds.
	 */
	uint64_t now() { return offset + millis(); };

};
