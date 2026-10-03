from dataclasses import dataclass
import pytest
import random
from typing import Protocol

from kiln_controller.device.protocol import *


class _Time[T](Protocol):  # impersonates the time module
    ## time module implementation
    def time(self) -> T: ...

    ## Testing functions (to make time do what we want...we can dream, right?)
    def advance(self, offset: float) -> None: ...


@dataclass
class _TimeImpl[T: int | float](_Time[T]):
    _type: type[T]
    _time: float = 0.0

    def time(self) -> T:
        return self._type(self._time)

    def advance(self, offset: float) -> None:
        self._time += offset


@pytest.fixture
def time() -> _Time[float]:
    return _TimeImpl(float, 1234567890.0)


@pytest.fixture
def uptime() -> _Time[int]:
    return _TimeImpl(int)


@pytest.fixture
def state() -> State:
    return State(StateEnum.IDLE)


@pytest.fixture
def memory() -> Memory:
    return Memory(1, 2, 3, 4)


@pytest.fixture
def temperature() -> Temperature:
    return Temperature(current=20, target=20, cold_junction=20, core=118)


@pytest.fixture
def sample(
    memory: Memory,
    temperature: Temperature,
    time: _Time[float],
) -> Sample:
    return Sample(
        int(time.time()), 1, StateEnum.COMPLETE | StateEnum.IDLE, temperature, 0, memory
    )


@pytest.fixture
def sample_ack_command(
    sample: Sample,
) -> SampleAckCommand:
    return SampleAckCommand(sample.timestamp)


@pytest.fixture
def telemetry(
    time: _Time[float], uptime: _Time[int], state: State, sample: Sample
) -> Telemetry:
    return Telemetry(int(time.time() * 1000), uptime.time(), state, 1, [sample])


@pytest.fixture
def set_time_command(time: _Time[float]) -> SetTimeCommand:
    return SetTimeCommand(int(time.time() * 1000))


@pytest.fixture
def start_command() -> StartCommand:
    return StartCommand()


@pytest.fixture
def stop_command() -> StopCommand:
    return StopCommand()


@pytest.fixture
def pause_command() -> PauseCommand:
    return PauseCommand()


@pytest.fixture
def resume_command() -> ResumeCommand:
    return ResumeCommand()


def test_state_roundtrip(state: State) -> None:
    assert state == State.unpack(state.pack())


def test_memory_roundtrip(memory: Memory) -> None:
    assert memory == Memory.unpack(memory.pack())


def test_temperature_roundtrip(temperature: Temperature) -> None:
    assert temperature == Temperature.unpack(temperature.pack())


def test_sample_roundtrip(sample: Sample) -> None:
    assert sample == Sample.unpack(sample.pack())


def test_telemetry_roundtrip(telemetry: Telemetry) -> None:
    assert telemetry == Telemetry.unpack(telemetry.pack())


def test_set_time_command_roundtrip(set_time_command: SetTimeCommand) -> None:
    assert set_time_command == SetTimeCommand.unpack(set_time_command.pack())
    assert set_time_command == CommandType.unpack(set_time_command.pack())


def test_start_command_roundtrip(start_command: StartCommand) -> None:
    assert start_command == StartCommand.unpack(start_command.pack())
    assert start_command == CommandType.unpack(start_command.pack())


def test_stop_command_roundtrip(stop_command: StopCommand) -> None:
    assert stop_command == StopCommand.unpack(stop_command.pack())
    assert stop_command == CommandType.unpack(stop_command.pack())


def test_pause_command_roundtrip(pause_command: PauseCommand) -> None:
    assert pause_command == PauseCommand.unpack(pause_command.pack())
    assert pause_command == CommandType.unpack(pause_command.pack())


def test_resume_command_roundtrip(resume_command: ResumeCommand) -> None:
    assert resume_command == ResumeCommand.unpack(resume_command.pack())
    assert resume_command == CommandType.unpack(resume_command.pack())


def test_sample_ack_command_roundtrip(sample_ack_command: SampleAckCommand) -> None:
    assert sample_ack_command == SampleAckCommand.unpack(sample_ack_command.pack())
    assert sample_ack_command == CommandType.unpack(sample_ack_command.pack())
