#ifndef SAMPLER_H
#define SAMPLER_H

#include <stdint.h>
#include "protocol.h"
#include "scheduler.h"

#define SAMPLE_RATE 500
#define SAMPLES_TO_BUFFER 128 // todo? base the number of samples in buffer on free memory

extern bool reboot;

#define BUFFER_INDEX_ERROR -1 // the requested buffer index is invalid

/**
 *
 */
typedef struct {
	protocol::Sample* buffer = NULL;
	uint16_t count = 0;
} SampleBuffer;

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
	void setNow(uint64_t now);

	/**
	 * @brief get the current synced time in milliseconds.
	 */
	uint64_t now() { return now_offset + millis(); };

	/**
	 * @brief Get the sample buffer.
	 *
	 * The address is stored into buffer and the number of samples in that
	 * buffer is returned. This may be less than sampleCount() returns if the
	 * samples are not contiguous (ie the ring buffer wraps). If there are
	 * no remaining samples buffer is NULL and zero is returned.
	 *
	 * index is used to specify which buffer is being requested. The currrent
	 * implementation accepts 0 and poissibly 1 if the current state wraps. All
	 * other values are invalid and INDEX_ERROR will be returned.
	 *
	 * TODO - locking...this essentially checks the samples out and they should
	 * not be overwriten. This isn't an issue currently with the sampler and
	 * sender in the same task, but if they are ever made concurrent the case
	 * where the sender "checks out" samples must take into account a concurrent
	 * sampling that advances current into the samples that were checked out,
	 * which could lead to partial reads of incomplete samples.
	 */
	void getSamples(int index, SampleBuffer* sampleBuffer);

	/**
	 * @brief discard count samples (presumably because they have been sent).
	 */
	void discard(uint16_t count);

};

#endif
