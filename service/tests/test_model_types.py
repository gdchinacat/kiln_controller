import unittest
import json
from datetime import time
from kiln_controller.common import PhaseType
from kiln_controller.service.models import PhaseBase


class PhaseTest(unittest.TestCase):

    def test_phase_type_roundtrip(self):
        phase = PhaseBase(
            name="name",
            phase_type=PhaseType.RAMP,
            duration=time(),
            ordinal=1,
            schedule_id=1,
        )
        assert isinstance(phase.duration, time)
        assert isinstance(phase.phase_type, PhaseType)

        d = phase.model_dump(
            mode="json"
        )  # asdict()  # todo use pydantic method directly
        print(d)
        json_ = json.dumps(d)

        phase_reconstituted = PhaseBase.model_validate_json(json_)
        assert isinstance(phase_reconstituted.duration, time)
        assert isinstance(phase_reconstituted.phase_type, PhaseType)
