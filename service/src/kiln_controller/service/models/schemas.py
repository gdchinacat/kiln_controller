"""
Pydantic schemas for request/response serialization.
"""

from datetime import time

from pydantic import BaseModel, Field, EmailStr

from ...common import PhaseType


class UserSchema(BaseModel):
    """Pydantic schema for a User."""

    id: int | None = Field(default=None, description="Primary key, assigned by the database.")
    name: str = Field(max_length=30, description="Display name of the user.")
    username: str = Field(max_length=16, description="Unique username (max 16 characters).")
    email: EmailStr | None = Field(default=None, description="Email address of the user.")
    phone_number: str | None = Field(default=None, description="Phone number of the user.")

    model_config = {"from_attributes": True}


class DeviceSchema(BaseModel):
    """Pydantic schema for a Device."""

    id: int | None = Field(default=None, description="Primary key, assigned by the database.")
    name: str = Field(max_length=30, description="Display name of the device.")
    host: str = Field(description="Hostname or IP address of the device.")
    port: int = Field(description="Port the device listens on.")
    url: str | None = Field(default=None, description="Optional URL for the device.")
    user_id: int = Field(description="ID of the user that manages this device.")
    description: str | None = Field(default=None, description="Optional description of the device.")

    model_config = {"from_attributes": True}


class ScheduleSchema(BaseModel):
    """Pydantic schema for a Schedule."""

    id: int | None = Field(default=None, description="Primary key, assigned by the database.")
    name: str = Field(max_length=30, description="Display name of the schedule.")
    user_id: int = Field(description="ID of the user that owns this schedule.")

    model_config = {"from_attributes": True}


class PhaseSchema(BaseModel):
    """Pydantic schema for a Phase."""

    id: int | None = Field(default=None, description="Primary key, assigned by the database.")
    name: str = Field(max_length=30, description="Display name of the phase.")
    ordinal: int = Field(description="Position of this phase within its schedule.")
    phase_type: PhaseType = Field(description="Whether the phase is a RAMP or CONSTANT.")
    duration: time | None = Field(default=None, description="How long the phase lasts (unset for RAMP).")
    rate: int | None = Field(default=None, description="Rate of temperature change in C/min (unset for CONSTANT).")
    temperature: int | None = Field(default=None, description="Target temperature in °C (unset for ambient).")
    schedule_id: int = Field(description="ID of the schedule this phase belongs to.")

    model_config = {"from_attributes": True}