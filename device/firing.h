#pragma once

#include <stdint.h>
#include "protocol.h"
#include "scheduler.h"

/**
 * @brief Firing manages the firing state.
 */
class Firing {
private:

public:
	Firing();

	void start(protocol::StartCommand* command);
	void stop(protocol::StopCommand* command);
	void pause(protocol::PauseCommand* command);
	void resume(protocol::ResumeCommand* command);

};
