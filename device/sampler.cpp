
#include <Arduino.h>
#include <stdlib.h>
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
		sample = &buffer[current];
		memset(sample, 0, sizeof(protocol::Sample));
		sample->timestamp = bucket_timestamp;
		sample->device_state = protocol::State::IDLE | protocol::State::DOOR_OPEN | protocol::State::COMMUNICATION_ERROR; //todo fill this out properly

		log_v("start sampling for %d[%d]", buffer[current].timestamp, current);
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
	uint32_t now = millis();
	protocol::Sample* sample = _currentSample(now);

	sample->sample_count += 1;

	sample->memory.size = ESP.getHeapSize();
	sample->memory.free = ESP.getFreeHeap();
	sample->memory.min =  ESP.getMinFreeHeap();
	sample->memory.max = ESP.getMaxAllocHeap();

	// todo all of the other metrics

	/*
	log_v("updated sample 0x%08x %d [%d] sample_count: %d",
			sample,
			buffer[current].timestamp,
			current,
			sample->sample_count);
	*/

	return true;
}

/**
 * @brief set the current time.
 */
void Sampler::setNow(uint64_t now) {
	int64_t newOffset = now - millis();
	int64_t delta = newOffset - now_offset;
	if (now_offset == 0 or abs(delta) > 1000) {
		now_offset = newOffset;
		log_i("updated time sync offset to %lld", now_offset);
	}
}

void Sampler::getSamples(int index, SampleBuffer* sampleBuffer) {
	sampleBuffer->count = 0;
	sampleBuffer->buffer = NULL;

	if (start != current) {
		if (index == 0) {
			sampleBuffer->count = ((current > start) ? current : buffer_size) - start;
			sampleBuffer->buffer = sampleBuffer->count ? &buffer[start] : NULL;
		} else if (index == 1 && current < start) {
			if (current) {
				sampleBuffer->count = current;
				sampleBuffer->buffer = buffer;
			}
		}
	}
	/*
	log_d("getSamples index: %d start: %d current: %d buffer_size: %d count: %d buffer idx: %d *_buffer: 0x%08x buffer: 0x%08x",
			index, start, current, buffer_size, sampleBuffer->count,
			sampleBuffer->buffer != NULL ? ((sampleBuffer->buffer - buffer) / sizeof(protocol::Sample)) : -1,
			sampleBuffer->buffer, buffer);
	*/
}


void Sampler::discard(uint16_t count) {
	start = (start + min(count, buffer_size)) % buffer_size;
}
