from kiln_controller.device.protocol import *

import time
import pytest


@pytest.fixture
def state() -> State:
    return State(StateEnum.IDLE)


@pytest.fixture
def memory() -> Memory:
    return Memory(1, 2, 3, 4)


@pytest.fixture
def sample(memory: Memory) -> Sample:
    return Sample(
        int(time.time()), 1, StateEnum.COMPLETE | StateEnum.IDLE, 20, 20, 20, 0, memory
    )


@pytest.fixture
def telemetry(state: State, sample: Sample) -> Telemetry:
    return Telemetry(state, 1, [sample])


@pytest.fixture
def telemetry_response() -> TelemetryResponse:
    return TelemetryResponse(123456789)


def test_state_roundtrip(state: State) -> None:
    assert state == State.unpack(state.pack())


def test_memory_roundtrip(memory: Memory) -> None:
    assert memory == Memory.unpack(memory.pack())


def test_sample_roundtrip(sample: Sample) -> None:
    assert sample == Sample.unpack(sample.pack())


def test_telemetry_roundtrip(telemetry: Telemetry) -> None:
    assert telemetry == Telemetry.unpack(telemetry.pack())


def test_telemetry_response_roundtrip(telemetry_response: TelemetryResponse) -> None:
    assert telemetry_response == TelemetryResponse.unpack(telemetry_response.pack())
