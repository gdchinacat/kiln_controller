import pytest
import random
from typing import Protocol

from kiln_controller.device.protocol import *


class _Time(Protocol):  # impersonates the time module
    ## time module implementation
    def time(self) -> float: ...

    ## Testing functions (to make time do what we want...we can dream, right?)
    def advance(self, offset: float) -> None: ...


class _TimeImpl(_Time):
    _time = 1234567890.0

    def time(self) -> float:
        return self._time

    def advance(self, offset: float) -> None:
        self._time += offset


@pytest.fixture
def time() -> _Time:
    return _TimeImpl()


@pytest.fixture
def state() -> State:
    return State(StateEnum.IDLE)


@pytest.fixture
def memory() -> Memory:
    return Memory(1, 2, 3, 4)


@pytest.fixture
def sample(memory: Memory, time: _Time) -> Sample:
    return Sample(
        int(time.time()), 1, StateEnum.COMPLETE | StateEnum.IDLE, 20, 20, 20, 0, memory
    )


@pytest.fixture
def telemetry(time: _Time, state: State, sample: Sample) -> Telemetry:
    return Telemetry(int(time.time() * 1000), state, 1, [sample])


@pytest.fixture
def set_time_command(time: _Time) -> SetTimeCommand:
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


def test_sample_roundtrip(sample: Sample) -> None:
    assert sample == Sample.unpack(sample.pack())


def test_telemetry_roundtrip(telemetry: Telemetry) -> None:
    assert telemetry == Telemetry.unpack(telemetry.pack())


def test_set_time_command_roundtrip(set_time_command: SetTimeCommand) -> None:
    assert set_time_command == SetTimeCommand.unpack(set_time_command.pack())


def test_start_command_roundtrip(start_command: StartCommand) -> None:
    assert start_command == StartCommand.unpack(start_command.pack())


def test_stop_command_roundtrip(stop_command: StopCommand) -> None:
    assert stop_command == StopCommand.unpack(stop_command.pack())


def test_pause_command_roundtrip(pause_command: PauseCommand) -> None:
    assert pause_command == PauseCommand.unpack(pause_command.pack())


def test_resume_command_roundtrip(resume_command: ResumeCommand) -> None:
    assert resume_command == ResumeCommand.unpack(resume_command.pack())
