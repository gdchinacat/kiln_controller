"""
User resource implementation.
"""

from ..models import User, UserORM
from .base import create_router

users_router = create_router(User, UserORM)
