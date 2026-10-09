from datetime import time
from enum import Enum
from typing import ClassVar

from rest_client import Resource, ResourceList, ResourceListDescriptor


class PhaseType(Enum):
    """the types of phases"""

    CONSTANT = "constant"
    RAMP = "ramp"


class Phase(Resource):
    _URL = "/phase"

    name: str
    schedule_id: int
    ordinal: int
    phase_type: PhaseType
    duration: time | None = None
    rate: int | None = None
    temperature: int | None = None


class Schedule(Resource):
    _URL = "/schedule"

    phases: ClassVar[ResourceListDescriptor[Phase, Schedule]] = ResourceListDescriptor(
        Phase
    )
    name: str
    user_id: int
