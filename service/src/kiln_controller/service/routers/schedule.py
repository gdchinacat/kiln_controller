"""
Application resources for schedule and related objects.
"""

from ..models import Schedule, ScheduleORM, Phase, PhaseORM
from .base import create_router

schedules_router = create_router(Schedule, ScheduleORM)
phases_router = create_router(Phase, PhaseORM, "/schedule/{schedule_id}")
