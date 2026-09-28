
#include <Arduino.h>
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
	buffer_size(SAMPLES_TO_BUFFER),
	scheduler([this]() {return this->sample();}, SAMPLE_RATE),
	buffer(new protocol::Sample[buffer_size]()) { }

void Sampler::setup() {
	// initialize the first sample time
	buffer[0].timestamp = _bucketTimestamp(millis());
}

void Sampler::loop() {
	scheduler.loop();
}

bool Sampler::sample() {
	protocol::Sample* sample = currentSample();

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

void Sampler::getSamples(int index, SampleBuffer* sampleBuffer) {
	// todo - this seems to have a bug with wrapping:
	// 143 metrics sent successfully for 13 samples for 60, 1790573890, 1790573895, 1790573900, 1790573905, 1790573910, 1790573915, 1790573920, 1790573925, 1790573930, 1790573935, 1790573940, 1790573945.
	// ...
	// 135 metrics sent successfully for 12 samples for 1790578930, 1790578935, 1790578940, 1790578945, 1790578950, 1790578955, 1790578960, 1790578965, 1790578970, 1790578975, 1790578980, 1790578985.
	// 11256 metrics sent successfully for 1023 samples for 1790573935, 1790573940, 1790573945,..., 1790579035, 1790579040, 1790579045.
	// 146 metrics sent successfully for 13 samples for 1790579045, 1790579050, 1790579055, 1790579060, 1790579065, 1790579070, 1790579075, 1790579080, 1790579085, 1790579090, 1790579095, 1790579100, 1790579105.
	///
	//
	// 1790573935 was sent twice, and the 1023 samples is the entire buffer...
	// something is clearly wrong with wrapping.
	// 1790579045 was also double sent

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
