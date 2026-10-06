from src.colmena_resume import load_state

def test_state_has_one_next_action():
    state=load_state()
    assert isinstance(state["next_single_action"],str)
    assert state["next_single_action"].strip()
