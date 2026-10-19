#pragma once

#include <stdint.h>

typedef enum class State : uint16_t;
#include "firing.h"

namespace protocol {

#pragma pack(push, 1)

/**
 * @enum MessageType
 * @brief Message identifiers sent to the kiln controller to trigger state changes or updates.
 *        These also act as the unique packet identifiers.
 */
enum class MessageType : uint8_t {
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

	/**
	 * @brief Tell the device samples have been received.
	 */
	SAMPLE_ACK = 6,

	/**
	 * @brief Telemetry message from device to service.
	 */
	TELEMETRY = 7,
};

/**
 * @struct Memory
 * @brief Memory usage statistics.
 */
struct Memory {
	/**
	 * @brief the total amount of memory on the heap.
	 *
	 * The minimum sampled value is reported.
	 */
	uint32_t size;

	/**
	 * @brief The amount of heap memory available for allocation.
	 *
	 * The minimum sampled value during the sample period is reported.
	 */
	uint32_t heap_free;

	/**
	 * @brief the minimum amount of memory free for allocations since startup.
	 *
	 * Although this value should only ever decrease as the controller executes
	 * it is oversampled and the minimum sampled value is reported.
	 */

	uint32_t min_heap_free;

	/**
	 * @brief The largest size that can be allocated.
	 *
	 * The minimum value in the sample period is reported because the use case
	 * is identifying impending allocation failures. A decrease in this value
	 * over time can indicate memory fragmentation.
	 */
	uint32_t largest_allocatable;

	/**
	 * @brief The size of the sample buffer.
	 */
	uint32_t sample_buffer_size;
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

class Message {
public:
	uint8_t type;
	Message(MessageType _type): type(static_cast<uint8_t>(_type)) {}
};

/**
 * @class Telemetry
 * @brief The periodic status update and request for command from server.
 */
class Telemetry : public Message {
public:
	Telemetry(
		uint64_t _timestamp,
		uint32_t _uptime,
		State _state,
		uint16_t _sample_count
	): Message(MessageType::TELEMETRY),
	  timestamp(_timestamp),
	  uptime(_uptime),
	  state(_state),
	  sample_count(_sample_count) {}

	/**
	 * @brief the time the device thinks it is (in milliseconds).
	 */
	uint64_t timestamp;

	/**
	 * @brief system clock time to reflect uptime (seconds).
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

/**
 * @brief Informs the device what the time is.
 */
class SetTimeCommand : public Message {
public:
	SetTimeCommand(uint64_t _timestamp)
	: Message(MessageType::SET_TIME),
	  timestamp(_timestamp) {}

	/**
	 * @brief the time the server thinks it is (in milliseconds).
	 */
	uint64_t timestamp;
};


/**
 * @brief Message start a firing.
 */
class StartCommand : public Message {
public:
    // todo include the schedule/phases.
	StartCommand(): Message(MessageType::START) {};
};

/**
 * @struct PauseCommand
 * @brief Message to pause a firing.
 */
class PauseCommand : public Message {
public:
	PauseCommand(): Message(MessageType::PAUSE) {};
};

/**
 * @struct ResumeCommand
 * @brief Message to resume a paused firing.
 */
class ResumeCommand : public Message {
public:
	ResumeCommand(): Message(MessageType::RESUME) {};
};

/**
 * @brief Message to cancel a firing.
 */
class StopCommand : public Message {
public:
	StopCommand(): Message(MessageType::STOP) {};
};

/**
 * @brief Message to confirm receipt of samples.
 */
class SampleAckMessage : public Message {
public:
	SampleAckMessage(uint32_t _timestamp):
		Message(MessageType::SAMPLE_ACK),
		timestamp(_timestamp) { };

    /**
	 * @brief The timestamp of the last sample received.
     */
    uint32_t timestamp;
};

#pragma pack(pop)


} // namespace protocol
