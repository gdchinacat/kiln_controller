
#include <Arduino.h>
#include "protocol.h"
#include "time_sync.h"


TimeSync::TimeSync() {

}

/**
 * @brief set the current time.
 */
void TimeSync::setTime(protocol::SetTimeCommand* command) {
	int64_t newOffset = command->timestamp - millis();
	int64_t delta = newOffset - offset;
	if (offset == 0 or abs(delta) > 1000) {
		offset = newOffset;
		log_i("updated time sync offset to %lld", offset);
	}
}
