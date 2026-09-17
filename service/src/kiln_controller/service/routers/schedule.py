"""
Application resources for schedule and related objects.
"""

from ..models import Schedule, ScheduleUpdate, ScheduleORM, Phase, PhaseUpdate, PhaseORM
from .base import create_router

schedules_router = create_router(
    Schedule, ScheduleORM, resource_update_type=ScheduleUpdate
)
phases_router = create_router(
    Phase, PhaseORM, "/schedule/{schedule_id}", resource_update_type=PhaseUpdate
)
