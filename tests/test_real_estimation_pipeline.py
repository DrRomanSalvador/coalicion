from pathlib import Path
import json
from src.real_estimation_pipeline import PipelineBlocked, materialize_observations

def test_materialization_blocks_without_territorial_observation(tmp_path):
    out=tmp_path/"observations.json"
    payload=materialize_observations([{
        "id":"p1","publication_date":"2026-10-07","pollster":"X",
        "source_id":"s","source_url":"https://example.invalid",
        "parties":{"PP":30,"PSOE":28,"VOX":15,"SUMAR":8,"PODEMOS":3}
    }],out)
    assert payload["status"]=="BLOCKED_NO_TERRITORIAL_OBSERVATION"
    assert payload["national_poll_count"]==1
    assert payload["territorial_poll_count"]==0
    assert json.loads(out.read_text())["policy"]["national_to_territorial_inference"] is False
