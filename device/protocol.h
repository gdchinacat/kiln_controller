#ifndef PROTOCOL_H
#define PROTOCOL_H

#include <stdint.h>
#include <variant>

namespace protocol {

/**
 * @enum State
 * @brief Bitmasks for the various states.
 *
 * The state is included in each sample, it is possible for it to be IDLE,
 * RUNNING, and ERROR all within a single sample, they are not mutually
 * exclusive. Any state that existed in the sample period should be set.
 *
 * When used for the current state (as in Telemetry request) the enum value is
 * used, not a bitmask.
 */
enum class State : uint16_t {

	/**
	 * @brief Device has a persistent error requiring operator attention and
	 * reset.
	 */
	ERROR = 1 << 0,

	/**
	 * @brief No firing was in progress.
	 */
    IDLE = 1 << 1,

	/**
	 * @brief Firing was in progress.
	 */
    RUNNING = 1 << 2,

	/**
	 * @brief Firing was paused.
	 *
	 * This can be due to a PAUSE command, the door being open, device not having
	 * time sync, etc. Any time the device is not actively controlling the element
	 * during a firing should report as paused.
	 */
    PAUSED = 1 << 3,

	/**
	 * @brief Firing completed.
	 *
	 * This state persists until it is cleared, typically by the acknowledging
	 * it with a STOP command, but could also be due to a device reset (although
	 * devices can persist it if they choose to).
	 */
    COMPLETE = 1 << 4,

	/**
	 * @brief Indicates an error reading the thermocouple temperature.
	 */
    THERMOCOUPLE_ERROR = 1 << 5,

	/**
	 * @brief Device initiated firing cancelation due to excessive temperature.
	 */
    OVER_TEMP = 1 << 6,

	/**
	 * @brief Device detected power was not applied to heating element when it
	 *        attempted to do so.
	 */
    HEATING_FAILED = 1 << 7,

	/**
	 * @brief Temperature deviated from target temperature by too much.
	 */
    REGULATION_FAILURE = 1 << 8,

	/**
	 * @brief Device was unable to communicate with server.
	 */
    COMMUNICATION_ERROR = 1 << 9,

	/**
	 * @brief The device door was open.
	 */
	DOOR_OPEN = 1 << 10

};

inline uint16_t operator|(State lhs, State rhs) {
	return static_cast<uint16_t>(lhs) | static_cast<uint16_t>(rhs);
}

inline uint16_t operator|(uint16_t lhs, State rhs) {
	return lhs | static_cast<uint16_t>(rhs);
}

inline uint16_t operator&(uint16_t lhs, State rhs) {
    return lhs & static_cast<uint16_t>(rhs);
}


/**
 * @enum CommandType
 * @brief Command identifiers sent to the kiln controller to trigger state changes or updates.
 *        These also act as the unique packet identifiers.
 */
enum class CommandType : uint8_t {
	/**
	 * @brief Start a firing.
	 */
    START = 0,

	/**
	 * @brief Stop a firing or acknowledge completion.
	 */
    STOP = 1,

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
	 * @brief The mean temperature in Celcius of the over the sample period.
	 */
    int16_t current_temp;

	/**
	 * @brief the temperature in Celsius the firmware is trying to maintain.
	 *
	 * This can change within the sample period, the last value is reported.
	 */
    int16_t target_temp;

	/**
	 * @brief The mean temperature in Celsius of the thermocouple cold junction.
	 */
    int16_t cold_junction_temp;

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
 * @struct TelemetryResponse
 * @brief The response to a Telemetry request.
 */
struct TelemetryResponse {
	// todo change TelemetryResponse to a SetTime command.
	/**
	 * @brief the time the server thinks it is (in milliseconds).
	 */
	uint64_t timestamp;
};

/**
 * @struct StartCommand
 * @brief Command start a firing.
 */
struct StartCommand {
    CommandType command_id = CommandType::START;
    // todo include the schedule/phases.
};

/**
 * @struct StopCommand
 * @brief Command to cancel a firing.
 */
struct StopCommand {
    CommandType command_id = CommandType::STOP;
};

/**
 * @struct PauseCommand
 * @brief Command to cancel a firing.
 */
struct PauseCommand {
    CommandType command_id = CommandType::PAUSE;
};

/**
 * @struct ResumeCommand
 * @brief Command to resume a paused firing.
 */
struct ResumeCommand {
    CommandType command_id = CommandType::RESUME;
};

#pragma pack(pop)

/**
 * @brief Command is a command the server responds to the kiln with.
 */
using Command = std::variant<
    StartCommand,
    StopCommand,
    PauseCommand,
    ResumeCommand
>;

} // namespace protocol

#endif // PROTOCOL_H
