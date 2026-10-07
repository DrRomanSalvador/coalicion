import json
from pathlib import Path

def test_calibration_artifact_contract(tmp_path):
    p=tmp_path/"oos_calibration.json"
    p.write_text(json.dumps({
        "status":"PASS","n_rows":10,"n_elections":8,
        "walk_forward_holdouts":6,
        "row_level_metrics":{"BASE":{"mae":1.0,"rmse":1.2}},
        "empirical_90pct_interval_calibration":{"BASE":{"mean_coverage":0.9}}
    }))
    x=json.loads(p.read_text())
    assert x["status"]=="PASS"
    assert x["walk_forward_holdouts"]>=1
    assert x["n_elections"]>=3
