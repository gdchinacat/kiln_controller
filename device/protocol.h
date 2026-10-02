#pragma once

#include <stdint.h>

typedef enum class State : uint16_t;
#include "firing.h"

namespace protocol {



/**
 * @enum CommandType
 * @brief Command identifiers sent to the kiln controller to trigger state changes or updates.
 *        These also act as the unique packet identifiers.
 */
enum class CommandType : uint8_t {
	/**
	 * @brief Start a firing.
	 */
    START = 1,

	/**
	 * @brief Temporarily pause a firing.
	 *
	 * Used to prepare kiln for being opened in a safe manner (avoid an alert).
	 */
    PAUSE = 2,

	/**
	 * @brief Resume firing after a pause.
	 */
    RESUME = 3,

	/**
	 * @brief Stop a firing or acknowledge completion.
	 */
    STOP = 4,


	/**
	 * @brief Tell the device what time it is.
	 */
	SET_TIME = 5,
};

#pragma pack(push, 1)

/**
 * @struct Memory
 * @brief Memory usage statistics.
 */
struct Memory {
	/**
	 * @brief the total amount of memory on the heap.
	 */
	uint32_t size;

	/**
	 * @brief the amount of memory available for allocation.
	 */
	uint32_t free;

	/**
	 * @brief the minimum amount of memory free for allocations.
	 */

	uint32_t min;
	/**
	 * @brief The max size that can be allocated.
	 *
	 * A decrease in this value over time can indicate memory fragmentation.
	 */
	uint32_t max;
};


struct Temperature {
	/**
	 * @brief The mean temperature in Celsius of the over the sample period.
	 */
    int16_t current;

	/**
	 * @brief the temperature in Celsius the firmware is trying to maintain.
	 *
	 * This can change within the sample period, the last value is reported.
	 */
    int16_t target;

	/**
	 * @brief The mean temperature in Celsius of the thermocouple cold junction.
	 */
    int16_t cold_junction;

	/**
	 * @brief The core temperature of the microcontroller.
	 */
    int16_t core;
};

/**
 * @struct Sample
 * @brief A sample of metrics reported to the service.
 */
struct Sample {

	/**
	 * @brief the unix time (seconds since epoch) of the start of the sample period.
	 *
	 * This requires the firmware be time synced with the service. Samples taken
	 * when the time was unsync'ed (between boot and first successful response
	 * may either be dropped or cached and filed in during time sync.
	 */
    uint32_t timestamp;

    /**
     * @brief the number of taken for the sample.
     */
    uint8_t sample_count;

    /**
     * @brief Bit field indicating the device state.
     *
     * Bits are set if their state occurred at any time during the sample period.
     */
    uint16_t device_state;

    /**
     * @brief the temperatures.
     */
    Temperature temperature;
	/**
	 * @brief The percentage of time the element had power applied over sample period.
	 */
    uint8_t duty_cycle;

    /**
     * @brief memory usage statistics.
     */
    Memory memory;

};

/**
 * @struct Telemetry
 * @brief The periodic status update and request for command from server.
 */
struct Telemetry {
	/**
	 * @brief the time the device thinks it is (in milliseconds).
	 */
	uint64_t timestamp;

	/**
	 * @brief system clock time to reflect uptime (~49 day overflow)
	 */
	uint32_t uptime;


	/**
	 * @brief the current state of the device.
	 */
	State state;

	/**
	 *
	 */
    uint16_t sample_count;

    /**
     * @brief Telemetry is immediately followed by sample_count samples.
	 *
	 * Declared as [0] to allow this to not be the terminal member of classes
	 * that contain it.
     */
    Sample samples[0];
};

class Command {
public:
	uint8_t type;
};

/**
 * @brief Informs the device what the time is.
 */
class SetTimeCommand : public Command {
public:
	/**
	 * @brief the time the server thinks it is (in milliseconds).
	 */
	uint64_t timestamp;
};


/**
 * @brief Command start a firing.
 */
class StartCommand : public Command {
public:
    CommandType type = CommandType::START;
    // todo include the schedule/phases.
};

/**
 * @struct PauseCommand
 * @brief Command to cancel a firing.
 */
class PauseCommand : public Command {
public:
    CommandType type = CommandType::PAUSE;
};

/**
 * @struct ResumeCommand
 * @brief Command to resume a paused firing.
 */
class ResumeCommand : public Command {
public:
    CommandType type = CommandType::RESUME;
};

/**
 * @brief Command to cancel a firing.
 */
class StopCommand : public Command {
public:
    CommandType type = CommandType::STOP;
};


#pragma pack(pop)


} // namespace protocol
