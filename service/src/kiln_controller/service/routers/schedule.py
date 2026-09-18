"""
Application resources for schedule and related objects.
"""

from ..models import (
    Schedule,
    ScheduleCreate,
    ScheduleUpdate,
    ScheduleORM,
    Phase,
    PhaseCreate,
    PhaseUpdate,
    PhaseORM,
)
from .base import create_router

schedules_router = create_router(
    "schedule",
    Schedule,
    ScheduleORM,
    resource_update_type=ScheduleUpdate,
    resource_create_type=ScheduleCreate,
)
phases_router = create_router(
    "phase",
    Phase,
    PhaseORM,
    "/schedule/{schedule_id}",
    resource_update_type=PhaseUpdate,
    resource_create_type=PhaseCreate,
)
