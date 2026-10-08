from src.reproducibility.hasher import sha256_json, reproducibility_record
from src.reproducibility.verifier import verify_same_result

def test_json_hash_is_order_independent():
    assert sha256_json({"b":2,"a":1}) == sha256_json({"a":1,"b":2})

def test_same_result_passes():
    assert verify_same_result(input_value={"x":1}, output_a={"y":[1,2]}, output_b={"y":[1,2]})["status"] == "PASS"

def test_code_fingerprint_is_present(tmp_path):
    p=tmp_path/"x.py"; p.write_text("x=1\n")
    r=reproducibility_record(input_value={"x":1}, output_value={"y":2}, code_files=[p])
    assert len(r["input_sha256"]) == 64
    assert len(r["output_sha256"]) == 64
    assert len(r["code_sha256"]) == 64
