from datetime import time
from enum import Enum

from rest_client import Resource, ResourceListDescriptor, RestClient


class PhaseType(str, Enum):
    """the types of phases"""

    CONSTANT = "constant"
    RAMP = "ramp"


class Phase(Resource["Schedule"]):
    _URL = "/phase"

    version: int | None = None
    name: str
    schedule_id: int | None = None
    ordinal: int
    phase_type: PhaseType
    duration: time | None = None
    rate: int | None = None
    temperature: int | None = None


class Schedule(Resource[RestClient]):
    _URL = "/schedule"

    version: int | None = None
    phases = ResourceListDescriptor(Phase)
    name: str
    user_id: int
