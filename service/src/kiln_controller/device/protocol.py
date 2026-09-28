"""
This module contains the protocol for communicating with the device. The
authoritative documentation is in kiln_controller/device/protocol.h .

Each protocol struct has a matching class that can read and write the bytes
that represent it.
for it.
"""

from abc import ABC
from collections.abc import Iterable
from dataclasses import dataclass, Field, fields, field, asdict
from enum import Enum
from itertools import pairwise
from struct import pack, unpack, Struct
from typing import Self, Protocol, ClassVar, Any

__all__ = (
    "Memory",
    "Sample",
    "State",
    "StateEnum",
    "Telemetry",
    "StartCommand",
    "StopCommand",
    "PauseCommand",
    "ResumeCommand",
    "SetTimeCommand",
    "Metrics",
)


def pages(buffer: bytes, offset: int, size: int) -> Iterable[bytes]:
    """generate pages of buffer with size bytes starting at offset"""
    yield from (
        buffer[start:end]
        for start, end in pairwise(range(offset, len(buffer) + 1, size))
    )


class DataclassInstance(Protocol):
    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]


class _Packable(DataclassInstance):
    """Base class to pack() and unpack() dataclasses."""

    struct: ClassVar[Struct]

    @classmethod
    def unpack(cls, buffer: bytes) -> Self:
        return cls(*cls.struct.unpack(buffer))

    def _value_to_pack(self, obj: Any) -> Any:
        """Get the value to emit for the value of one of self's fields."""
        match obj:
            case _Packable():
                return obj.pack()
            case Iterable():
                # The struct format strings specify these as zero bytes, so
                # this emits them as zero bytes. It *could* emit the proper
                # bytes, but the value is ignored by the format. Subclasses
                # must override pack() for now to do their list field packing
                # themselves. See Telemetry.pack(). todo? move this logic into
                # _Packable.pack()?
                return b""
            case Enum():
                return obj.value
            case _:
                return obj

    def field_values(self) -> Iterable[Any]:
        """
        Get the field values that will be packed.

        Subclasses can override this to inject fields that aren't user settable
        and aren't in the dataclass fields. For example, _Command uses this to
        insert the automatically managed command_type.
        """
        yield from (getattr(self, field.name) for field in fields(self))

    def pack(self) -> bytes:
        """return the byte packed representation."""
        pack_values = (self._value_to_pack(value) for value in self.field_values())
        return self.struct.pack(*pack_values)


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
    START = 1
    PAUSE = 2
    RESUME = 3
    STOP = 4
    SET_TIME = 5


class Metrics(_Packable):
    def items(self) -> Iterable[tuple[str, Any]]:
        yield from ((field.name, getattr(self, field.name)) for field in fields(self))


@dataclass
class Memory(Metrics):
    struct: ClassVar[Struct] = Struct("<IIII")
    size: int  # uint32_t
    free: int  # uint32_t
    min: int  # uint32_t
    max: int  # uint32_t


@dataclass
class Sample(Metrics):
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
        self = super().unpack(buffer[: cls.struct.size])
        self.samples = [
            Sample.unpack(_buffer)
            for _buffer in pages(buffer, self.struct.size, Sample.struct.size)
        ]
        return self

    def pack(self) -> bytes:
        return b"".join((super().pack(), *(sample.pack() for sample in self.samples)))


@dataclass
class _Command(_Packable, ABC):
    struct: ClassVar[Struct] = Struct("<B")
    command_type: ClassVar[CommandType]

    def field_values(self) -> Iterable[Any]:
        # insert command type into fields to pack
        yield from (self.command_type, *super().field_values())

    @classmethod
    def unpack(cls, buffer: bytes) -> Self:
        args = cls.struct.unpack(buffer)
        if args[0] != cls.command_type.value:
            raise TypeError
        return cls(*args[1:])


@dataclass
class SetTimeCommand(_Command):
    struct: ClassVar[Struct] = Struct(_Command.struct.format + "Q")
    command_type: ClassVar[CommandType] = field(
        default=CommandType.SET_TIME, init=False
    )
    timestamp: int


@dataclass
class StartCommand(_Command):
    struct: ClassVar[Struct] = Struct(_Command.struct.format + "")
    command_type = CommandType.START
    # todo include the schedule/phases.


@dataclass
class PauseCommand(_Command):
    command_type = CommandType.PAUSE


@dataclass
class ResumeCommand(_Command):
    command_type = CommandType.RESUME


@dataclass
class StopCommand(_Command):
    command_type = CommandType.STOP
