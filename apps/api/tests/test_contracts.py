import json
from pathlib import Path

import pytest

from app.schemas.api import CampaignCreate, ImportReport, SimulationPayment

EXAMPLES = Path(__file__).resolve().parents[3] / "contracts" / "examples"


@pytest.mark.parametrize(
    "name,model",
    [
        ("campaign-create.json", CampaignCreate),
        ("payment-request.json", SimulationPayment),
        ("import-report.json", ImportReport),
    ],
)
def test_shared_examples_conform_to_actual_request_and_response_schemas(name, model):
    model.model_validate(json.loads((EXAMPLES / name).read_text()))
