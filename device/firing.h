#pragma once

#include <stdint.h>

namespace protocol {
typedef struct StartCommand;
typedef struct PauseCommand;
typedef struct ResumeCommand;
typedef struct StopCommand;
};

#include "protocol.h"


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
	 *		attempted to do so.
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

constexpr const char* str(State state) {
	//todo? extend this to support bitmask usage? That would require changing
	//      from constants to string building which I am trying to avoid.
    switch (state) {
        case State::ERROR:               return "error";
        case State::IDLE:                return "idle";
        case State::RUNNING:             return "running";
        case State::PAUSED:              return "paused";
        case State::COMPLETE:            return "complete";
        case State::THERMOCOUPLE_ERROR:  return "thermocouple error";
        case State::OVER_TEMP:           return "over temp";
        case State::HEATING_FAILED:      return "heating failed";
        case State::REGULATION_FAILURE:  return "regulation failure";
        case State::COMMUNICATION_ERROR: return "communication error";
        case State::DOOR_OPEN:           return "door open";
        default:                         return "Unknown";
    }
}

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
 * @brief Firing manages the firing state.
 */
class Firing {
private:
	State state = State::IDLE;
	void setState(State state);

public:
	Firing();

	State currentState() { return state; };

	void start(protocol::StartCommand* command);
	void stop(protocol::StopCommand* command);
	void pause(protocol::PauseCommand* command);
	void resume(protocol::ResumeCommand* command);

};
