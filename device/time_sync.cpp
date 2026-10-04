
#include <Arduino.h>
#include "protocol.h"
#include "time_sync.h"


TimeSync::TimeSync() {

}

/**
 * @brief set the current time.
 */
void TimeSync::setTime(protocol::SetTimeCommand* command) {
	offset = (int64_t)command->timestamp - uptime();
	log_i("updated time sync offset to %lld", offset);
}
