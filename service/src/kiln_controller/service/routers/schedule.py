"""
Application resources for schedule and related objects.
"""

from ..models import ScheduleBase, Schedule, PhaseBase, Phase
from .base import create_router

schedules_router = create_router(ScheduleBase, Schedule)
phases_router = create_router(PhaseBase, Phase, "/schedule/{schedule_id}")
