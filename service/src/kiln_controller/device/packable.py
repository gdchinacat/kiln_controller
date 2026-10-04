from collections.abc import Callable
from dataclasses import fields, Field
import struct
from typing import ClassVar, Self, Protocol, Any

from .base import managed_dataclass, managed_field


class DataclassInstance(Protocol):
    __dataclass_fields__: ClassVar[dict[str, Field[Any]]]


class BaseMetric(DataclassInstance):
    __slots__ = ()
    struct: ClassVar[struct.Struct]

    def pack(self) -> bytes:
        field_values = (
            (
                value.pack()
                if isinstance(value := getattr(self, f.name), BaseMetric)
                else value
            )
            for f in fields(self)
        )
        return self.struct.pack(*field_values)

    @classmethod
    def unpack(cls, buffer: bytes) -> Self:
        unpacked_data = cls.struct.unpack(buffer)
        return cls(*unpacked_data)


def to_metric[M: BaseMetric](metric_cls: type[M]) -> Callable[[bytes], M]:
    def converter(value: bytes) -> M:
        return metric_cls.unpack(value)

    return converter


def to_metric_sequence[M: BaseMetric](
    metric_cls: type[M], count: int
) -> Callable[[bytes | list[M]], list[M]]:
    """Generates a closure to parse a contiguous chunk of bytes or list into an array of sub-metrics."""

    def converter(value: bytes | list[M]) -> list[M]:
        if isinstance(value, bytes):
            size = metric_cls.struct.size
            return [
                metric_cls.unpack(value[i * size : (i + 1) * size])
                for i in range(count)
            ]
        return value

    return converter


if __name__ == "__main__":

    @managed_dataclass
    class Temperature(BaseMetric):
        struct = struct.Struct(">hh")
        current: int
        target: int

    @managed_dataclass
    class Telemetry(BaseMetric):
        struct = struct.Struct(">B 4s")

        state: int
        # Type Checker infers: ManagedPropertyDescriptor[Temperature, bytes]
        temperature: Temperature = managed_field(to_metric(Temperature))

    print(Temperature.unpack((temperature := Temperature(20, 30)).pack()))
    telemetry = Telemetry(1, temperature)
    print(telemetry)
    print(Telemetry.unpack(telemetry.pack()))
