"""
This package exposes the python SDK (client) for the kiln_controller service.

The client is pretty general purpose, it should not have anything
kiln_controller specific.

TODO - docs and examples (you can't read this code and infer how to use it
       because it is way too abstract by dynamically generating the types
       you need to use).
TODO - The client should really take a URL that identifies the server to work
       with. It should download the openapi.json and create the proper pydantic
       models (do not import anything from kiln_controller.common or .service).
TODO - package this as a separate library that has no kiln_controller specific
       functionality or dependencies. It should be able to work with any CRUD
       object model. It should be extensible to add the client-side usability
       specific services want (ie automatic ordinal reordering, higher-level
       workflows such as user onboarding, etc).
"""

from ..common.validators import ValidationErrors, ValidationError
from ._base import ClientException, NotFoundException, UnauthorizedException
from .client import (
    Client,
    User,
    Device,
    Schedule,
    Phase,
    PhaseType,
)

__all__ = [
    "Client",
    "ClientException",
    "NotFoundException",
    "UnauthorizedException",
    "ValidationError",
    "ValidationErrors",
    "User",
    "Device",
    "Schedule",
    "Phase",
    "PhaseType",
]
