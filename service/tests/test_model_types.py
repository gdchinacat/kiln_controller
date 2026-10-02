import unittest
import json
from datetime import time
from kiln_controller.common.enums import PhaseType
from kiln_controller.service.models import Phase, DeviceCreate, DeviceORM, SessionMaker


def test_phase_type_roundtrip() -> None:
    phase = Phase(
        id=1,
        name="name",
        phase_type=PhaseType.RAMP,
        duration=time(),
        ordinal=1,
        schedule_id=1,
    )
    assert isinstance(phase.duration, time)
    assert isinstance(phase.phase_type, PhaseType)

    d = phase.model_dump(mode="json")
    json_ = json.dumps(d)

    phase_reconstituted = Phase.model_validate_json(json_)
    assert isinstance(phase_reconstituted.duration, time)
    assert isinstance(phase_reconstituted.phase_type, PhaseType)


async def test_ids_are_not_reused(sessionmaker: SessionMaker) -> None:
    """
    Ensure deleting a resource and then creating a new one does not reuse id.

    External services may have ids so they should not be reused to avoid
    confusion between resources.
    """
    device_dict = dict(name="name", auth_token="", user_id=1)
    async with sessionmaker() as session:
        device1 = DeviceORM.model_validate(device_dict)
        session.add(device1)
        await session.commit()

    async with sessionmaker() as session:
        await session.delete(device1)
        await session.commit()
        assert not await session.get(DeviceORM, device1.id)

    async with sessionmaker() as session:
        device2 = DeviceORM.model_validate(device_dict)
        session.add(device2)
        await session.commit()

        assert device1.id and device2.id
        assert device1.id != device2.id


DeviceCreate
