
#include <Arduino.h>
#include <esp32-hal.h>
#include <stdlib.h>
#include "firing.h"
#include "protocol.h"
#include "sampler.h"

extern Firing firing;

void Sampler::_sampleMemory() {

	buffer[current].memory.size = ESP.getHeapSize();
	buffer[current].memory.free = ESP.getFreeHeap();
	buffer[current].memory.min = ESP.getMinFreeHeap();
	buffer[current].memory.max = ESP.getMaxAllocHeap();

}

uint16_t Sampler::_wrap(uint16_t index) {
	return (index >= buffer_size) ? 0 : index;
}

uint32_t Sampler::_bucketTimestamp(unsigned long now) {
	unsigned long long adjusted = timeSync.now();
	return (uint32_t)((adjusted - adjusted % sample_period)/1000);

}

/**
 * @brief get the current sample to update
 */
protocol::Sample* const Sampler::currentSample() {
	unsigned long now = millis();
	protocol::Sample* sample = &buffer[current];
	uint32_t bucketTimestamp = _bucketTimestamp(now);
	if (bucketTimestamp > sample->timestamp) {
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
		sample->timestamp = bucketTimestamp;
		sample->device_state |= static_cast<uint16_t>(firing.currentState());

		log_v("start sampling for %d[%d]", buffer[current].timestamp, current);
		if (last_timestamp + (sample_period / 1000) != sample->timestamp) {
			log_w("missed %d samples", (sample->timestamp - last_timestamp) / sample_period);
		}
	}

	return sample;
}

Sampler::Sampler(uint16_t _sample_period):
	sample_period(_sample_period),
	buffer_size(SAMPLE_BUFFER_SIZE),
	scheduler([this]() {return this->sample();}, SAMPLE_RATE),
	buffer(new protocol::Sample[buffer_size]()) { }

void Sampler::setup() {
	// initialize the first sample time
	buffer[0].timestamp = _bucketTimestamp(millis());
}

void Sampler::loop() {
	scheduler.loop();
}

#define min(A, B) (A < B ? A : B)
#define max(A, B) (A > B ? A : B)
//todo? - avg implementation is not great due to integer math with division and
//        recalculating total then dividing. Should samples be fixed up on the
//        way out (taking resends into account)? Should the server calculate
//        value based on sample_count? Which fields to apply this to?
#define avg(COUNT, A, B) ((A * COUNT + B) / (COUNT + 1))

bool Sampler::sample() {
	protocol::Sample* sample = currentSample();

	sample->sample_count += 1;

	sample->memory.size = min(sample->memory.size, ESP.getHeapSize());
	sample->memory.free = min(sample->memory.free, ESP.getFreeHeap());
	sample->memory.min = min(sample->memory.min, ESP.getMinFreeHeap());
	sample->memory.max = min(sample->memory.max, ESP.getMaxAllocHeap());

	protocol::Temperature* temperature = &(sample->temperature);
	temperature->core = avg(sample->sample_count - 1,\
						   temperature->core,\
						   temperatureRead());

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
}


void Sampler::discard(uint16_t count) {
	start = (start + min(count, buffer_size)) % buffer_size;
}
