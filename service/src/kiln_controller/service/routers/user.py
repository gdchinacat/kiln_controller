"""
User resource implementation.
"""

from ..models import User, UserCreate, UserORM
from .base import create_router

users_router = create_router(User, UserORM, resource_create_type=UserCreate)
