from dataclasses import dataclass, field, fields
from typing import Any, Callable, dataclass_transform


class ManagedPropertyDescriptor[T, In]:
    """Manages explicit data transformation transparently over a class attribute."""

    def __init__(self, name: str, target_type: type[T], converter: Callable[[In], T]):
        self._internal_name: str = f"_{name}"
        self.target_type: type[T] = target_type
        self.converter: Callable[[In], T] = converter

    # When accessed on the instance, it returns the target type 'T'
    def __get__(self, instance: object, owner: type[object]) -> T | Any:
        if instance is None:
            return self
        return getattr(instance, self._internal_name)

    # The setter strictly enforces that the value must match 'T' or the input type 'In'
    def __set__(self, instance: object, value: T | In) -> None:
        # If the input type matches the expected target structure, bypass the converter
        match value:
            case self.target_type():
                setattr(instance, self._internal_name, value)
            case _:
                setattr(instance, self._internal_name, self.converter(value))


def managed_field[T, In](converter: Callable[[In], T], **kwargs: Any) -> Any:
    """Configures a dataclass field to redirect initialization input through a property converter."""
    metadata = kwargs.pop("metadata", {})
    metadata["transform_on_init"] = True
    metadata["transform_converter"] = converter
    return field(metadata=metadata, **kwargs)


@dataclass_transform(field_specifiers=(managed_field, field))
def managed_dataclass(cls: type) -> type:
    """Decorator enabling declarative field conversion interceptors on a standard dataclass."""
    annotations: dict[str, type] = getattr(cls, "__annotations__", {})
    extra_attributes: list[str] = []
    convert_fields: list[tuple[str, type, Callable[[Any], Any]]] = []

    for name, annotation in annotations.items():
        default_val = getattr(cls, name, None)
        if hasattr(default_val, "metadata") and default_val.metadata.get(
            "transform_on_init"
        ):
            extra_attributes.append(f"_{name}")
            convert_fields.append(
                (name, annotation, default_val.metadata["transform_converter"])
            )

    existing_slots = set(getattr(cls, "__slots__", ()))
    if existing_slots or hasattr(cls, "__match_args__"):
        updated_slots = list(existing_slots)
        for name in annotations:
            if name not in existing_slots:
                updated_slots.append(name)
        for priv_attr in extra_attributes:
            if priv_attr not in existing_slots:
                updated_slots.append(priv_attr)
        cls.__slots__ = tuple(updated_slots)

    cls = dataclass(cls)

    for field_name, field_type, field_converter in convert_fields:
        # Injects the descriptor which explicitly maps the types without using Any
        setattr(
            cls,
            field_name,
            ManagedPropertyDescriptor(field_name, field_type, field_converter),
        )

    return cls
