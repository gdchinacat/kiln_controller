"""
User resource implementation.
"""

from ..models import UserBase, User
from .base import create_router

users_router = create_router(UserBase, User)
