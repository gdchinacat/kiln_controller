"""
This module contains the protocol for communicating with the device. The
authoritative documentation is in kiln_controller/device/protocol.h .

Each protocol struct has a matching class that can read and write the bytes
that represent it.
for it.
"""

from abc import ABC
from dataclasses import dataclass, Field, fields
from enum import Enum
from struct import pack, unpack, Struct
from typing import Self, Protocol, ClassVar, Any

__all__ = (
    "Memory",
    "Sample",
    "State",
    "StateEnum",
    "Telemetry",
    "TelemetryResponse",
)


class DataclassInstance(Protocol):
    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]


class _Packable(DataclassInstance):
    """Base class to pack() and unpack() dataclasses."""

    struct: ClassVar[Struct]

    @classmethod
    def unpack(cls, buffer: bytes) -> Self:
        return cls(*cls.struct.unpack(buffer))

    def __pack_convert(self, obj: Any) -> Any:
        match obj:
            case _Packable():
                return obj.pack()
            case list():
                return bytes().join(self.__pack_convert(x) for x in obj)
            case Enum():
                return obj.value
            case _:
                return obj

    def pack(self) -> bytes:
        """return the byte packed representation."""
        # Don't use dataclasses.astuple because it recurses and converts nested
        # _Packable into tuples and we need them to be pack()'ed into bytes.
        _fields = [
            self.__pack_convert(getattr(self, field.name)) for field in fields(self)
        ]
        return self.struct.pack(*_fields)


class StateEnum(Enum):
    ERROR = 1 << 0
    IDLE = 1 << 1
    RUNNING = 1 << 2
    PAUSED = 1 << 3
    COMPLETE = 1 << 4
    THERMOCOUPLE_ERROR = 1 << 5
    OVER_TEMP = 1 << 6
    HEATING_FAILED = 1 << 7
    REGULATION_FAILURE = 1 << 8
    COMMUNICATION_ERROR = 1 << 9
    DOOR_OPEN = 1 << 10

    def __or__(self, other: int | StateEnum) -> int:
        return self.value | (other.value if isinstance(other, StateEnum) else other)


@dataclass
class State(_Packable):
    struct: ClassVar[Struct] = Struct("<H")
    state: StateEnum

    def __post_init__(self) -> None:
        self.state = StateEnum(self.state)


class CommandType(Enum):
    START = 0
    STOP = 1
    PAUSE = 2
    RESUME = 3


@dataclass
class Memory(_Packable):
    struct: ClassVar[Struct] = Struct("<IIII")
    size: int  # uint32_t
    free: int  # uint32_t
    min: int  # uint32_t
    max: int  # uint32_t


@dataclass
class Sample(_Packable):
    struct: ClassVar[Struct] = Struct(f"<IBHhhhB{Memory.struct.size}s")
    timestamp: int  # uint32_t
    count: int  # uint8_t
    state: int  # uint16_t
    current_temp: int  # int16_t
    target_temp: int  # int16_t
    cold_junction_temp: int  # int16_t
    duty_cycle: int  # uint8_t
    memory: Memory

    def __post_init__(self) -> None:
        # todo factor this out into the base class, implementations shouldn't
        # have to do this..it defeats the purpose of the framework
        if isinstance(self.memory, bytes):
            self.memory = Memory.unpack(self.memory)


@dataclass
class Telemetry(_Packable):
    struct: ClassVar[Struct] = Struct(f"<Q{State.struct.size}sH0s")

    timestamp_ms: int
    state: State
    sample_count: int  # uint16_t
    samples: list[Sample]

    def __post_init__(self) -> None:
        # todo factor this out into the base class, implementations shouldn't
        # have to do this..it defeats the purpose of the framework
        if isinstance(self.state, bytes):
            self.state = State.unpack(self.state)

    @classmethod
    def unpack(cls, buffer: bytes) -> Self:
        if len(buffer) < cls.struct.size:
            raise ValueError(
                f"{cls.__name__} requires {cls.struct.size} but got {len(buffer)}"
            )
        offset = cls.struct.size
        self = super().unpack(buffer[:offset])
        self.samples = []

        # todo - refactor this logic for writing lists onto base class
        for _ in range(self.sample_count):
            self.samples.append(
                Sample.unpack(buffer[offset : offset + Sample.struct.size])
            )
            offset += Sample.struct.size
        return self

    def pack(self) -> bytes:
        buffer = super().pack()
        return b"".join((super().pack(), *(sample.pack() for sample in self.samples)))


@dataclass
class TelemetryResponse(_Packable):
    struct: ClassVar[Struct] = Struct(f"<Q")
    timestamp: int


@dataclass
class _Command(_Packable):
    struct: ClassVar[Struct] = Struct("<B")
    command_type: CommandType


@dataclass
class StartCommand(_Command):
    struct: ClassVar[Struct] = Struct(_Command.struct.format + "")
    command_type = CommandType.START
    # todo include the schedule/phases.


@dataclass
class StopCommand(_Command):
    command_id = CommandType.STOP


@dataclass
class PauseCommand(_Command):
    command_id = CommandType.PAUSE


@dataclass
class ResumeCommand(_Command):
    command_type = CommandType.RESUME
