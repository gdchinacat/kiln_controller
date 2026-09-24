
#include <Arduino.h>
#include "protocol.h"
#include "sampler.h"

void Sampler::_sampleMemory() {

	buffer[current].memory.size = ESP.getHeapSize();
	buffer[current].memory.free = ESP.getFreeHeap();
	buffer[current].memory.min = ESP.getMinFreeHeap();
	buffer[current].memory.max = ESP.getMaxAllocHeap();

}

uint16_t Sampler::_wrap(uint16_t index) {
	return (index >= buffer_size) ? 0 : index;
}

uint32_t Sampler::_bucket_timestamp(uint32_t now) {
	uint64_t adjusted = now_offset + now;
	return (uint32_t)((adjusted - adjusted % sample_period)/1000);

}

/**
 * @brief get the current sample to update
 */
protocol::Sample* const Sampler::_currentSample(uint32_t now) {
	protocol::Sample* sample = &buffer[current];
	uint32_t bucket_timestamp = _bucket_timestamp(now);
	if (bucket_timestamp > sample->timestamp) {
		uint32_t last_timestamp = sample->timestamp;

		// Advance the current sample, wrapping if necessary and advancing start
		// if buffer is full.
		current = _wrap(current + 1);
		if (current == start) {
			start = _wrap(start + 1);
		}

		// Initialize the new sample.
		memset(sample, 0, sizeof(protocol::Sample));
		sample = &buffer[current];
		sample->timestamp = bucket_timestamp;

		log_i("start sampling for %d[%d]", buffer[current].timestamp, current);
		if (last_timestamp + (sample_period / 1000) != sample->timestamp) {
			log_w("missed %d samples", (sample->timestamp - last_timestamp) / sample_period);
		}
	}

	return sample;
}

Sampler::Sampler(uint16_t _sample_period):
	sample_period(_sample_period),
	buffer_size(SAMPLES_TO_BUFFER),
	scheduler([this]() {return this->sample();}, SAMPLE_RATE),
	buffer(new protocol::Sample[buffer_size]()) { }

void Sampler::setup() {
	// initialize the first sample time
	buffer[0].timestamp = _bucket_timestamp(millis());
}

void Sampler::loop() {
	scheduler.loop();
}

bool Sampler::sample() {
	auto now = millis();
	auto sample = _currentSample(now);

	sample->sample_count += 1;

	log_i("updated sample %d [%d] sample_count: %d",
			buffer[current].timestamp,
			current,
			sample->sample_count);
	return true;
}

/**
 * @brief set the current time.
 */
void Sampler::set_now(uint64_t now) {
	now_offset = now - millis();
}
