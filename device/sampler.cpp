
#include <Arduino.h>
#include <esp32-hal.h>
#include <stdlib.h>
#include "firing.h"
#include "protocol.h"
#include "sampler.h"

extern Firing firing;

uint16_t Sampler::_wrap(uint16_t index) {
	return (index >= buffer_size) ? 0 : index;
}

uint32_t Sampler::_bucketTimestamp(uint64_t timestamp) {
	return (uint32_t)((timestamp - timestamp % samplePeriod)/1000);
}

/**
 * @brief get the current sample to update
 */
protocol::Sample* const Sampler::currentSample() {
	uint32_t bucketTimestamp = _bucketTimestamp(timeSync.now());
	protocol::Sample* sample = &buffer[current];
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
		sample->device_state = static_cast<uint16_t>(firing.currentState());

		log_v("start sampling for %d[%d]", buffer[current].timestamp, current);
		if (last_timestamp + (samplePeriod / 1000) != sample->timestamp) {
			log_w("missed %d samples", (sample->timestamp - last_timestamp) / samplePeriod);
		}
	}

	return sample;
}

Sampler::Sampler(uint16_t _samplePeriod):
	samplePeriod(_samplePeriod),
	buffer_size(SAMPLE_BUFFER_SIZE),
	scheduler([this]() {return this->sample();}, SAMPLE_RATE),
	buffer(new protocol::Sample[buffer_size]()) { }

void Sampler::setup() {
	// initialize the first sample time
	buffer[0].timestamp = _bucketTimestamp(timeSync.now());
}

void Sampler::loop() {
	scheduler.loop();
}

//todo? - avg implementation is not great due to integer math with division and
//        recalculating total then dividing. Should samples be fixed up on the
//        way out (taking resends into account)? Should the server calculate
//        value based on sample_count? Which fields to apply this to?
#define avg(COUNT, A, B) ((A * COUNT + B) / (COUNT + 1))

bool Sampler::sample() {
	protocol::Sample* sample = currentSample();

	sample->sample_count += 1;

	_sampleMemory(&sample->memory);

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

#define min(A, B) (A > 0 && A < B ? A : B)
void Sampler::_sampleMemory(protocol::Memory* memory) {
	memory->size = min(memory->size, ESP.getHeapSize());
	memory->heap_free = min(memory->heap_free, ESP.getFreeHeap());
	memory->min_heap_free = min(memory->min_heap_free, ESP.getMinFreeHeap());
	memory->largest_allocatable = min(memory->largest_allocatable, ESP.getMaxAllocHeap());
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

void Sampler::discard(uint32_t timestamp) {
	// todo? this feels fragile...should some sort of validation be done that
	//       the discarded samples are actually below the timestamp? Should a
	//       different algorithm be used (such as scanning from start to
	//       current discarding samples along the way? Most of my worries are
	//       that timesync, or long buffer periods or delayed sampling could
	//       accidentally being dropped incorrectly (if the calculated samples
	//       skip a sample here and there the timestamp for the calculated
	//       new start could be much greater than timestamp and the ones before
	//       it also greater than timestamp. Also, the initial time sync is not
	//       handled well, the jump from near zero to 1.7billion "drops" a lot
	//       of samples and I doubt that is being handled in a well defined way.
	//       This isn't fundamental to the design so is being deferred since
	//       this seems to work well even under server up/down periods.
	//log_d("discard original timestamp: %d", timestamp);
	timestamp = _bucketTimestamp(((uint64_t)timestamp) * 1000);
	//log_d(" discard aligned timestamp: %d", timestamp);
	int count = (((int64_t)timestamp - buffer[start].timestamp) * 1000) / samplePeriod;
	count += 1;  // include the timestamp bucket itself
	//log_d("                     count: %d", count);
	if (count >= 0) {
		int buffered_samples = ((current >= start) ? current : (current + buffer_size)) - start;
		//log_d("        samples   buffered: %d", buffered_samples);
		if (count > buffered_samples) {
			log_e("got sample ack for %d resulting in count %d but only %d buffered",
					timestamp, count, buffered_samples);
			count = buffered_samples;
		}
		start = (start + count) % buffer_size;
		log_d("advanced %d samples to %d (%d)", count, start, buffer[start].timestamp);
	} else {
		log_e("ignoring sample discard request for timestamp %d with negative count=%d",
				timestamp, count);
	}
}
