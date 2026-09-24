#ifndef SAMPLER_H
#define SAMPLER_H

#include <stdint.h>
#include "protocol.h"
#include "scheduler.h"

#define SAMPLE_RATE 500
#define SAMPLES_TO_BUFFER 10 // todo? base the number of samples in buffer on free memory

extern bool reboot;

/**
 * @brief Sampler is responsible for sampling the hardware and providing the
 * samples for Telemetry to report.
 */
class Sampler {
private:
	/**
	 * @brief the sample period.
	 *
	 * This is the number of milliseconds in each sample. The scheduler interval
	 * is (typically) set to ensure oversampling to smooth out noise in
	 * measurements like temperature.
	 */
	uint16_t sample_period;

	/**
	 * @brief The scheduler that manages when to sample.
	 */
	Scheduler scheduler;

	/**
	 * @brief the number of samples in the buffer.
	 */
	uint16_t buffer_size;

	/**
	 * @brief buffer is the ring buffer.
	 */
	protocol::Sample* const buffer;

	/**
	 * @brief start is the first sample in the buffer.
	 */
	uint16_t start = 0;

	/**
	 * @brief current is the sample for the current sample period.
	 */
	uint16_t current = 0;

	bool sample();

	/**
	 * @brief get the sample now is in.
	 *
	 * This moves the sample forward, possibly dropping a sample if the ring
	 * buffer is full.
	 */
	protocol::Sample* const _currentSample(uint32_t now);

	/**
	 * @brief wrap the index if it exceeds the length of the buffer.
	 */
	uint16_t _wrap(uint16_t index);

	void _sampleMemory();

	uint32_t _bucket_timestamp(uint32_t now);

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
	uint64_t now_offset = 0;
public:
	Sampler(uint16_t _sample_period);
	void loop();
	void setup();

	/**
	 * @brief tell the sampler what time it is now.
	 */
	void set_now(uint64_t now);

};

#endif
