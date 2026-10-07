import pytest
from src.oos_pipeline import load_poll_observations, run_oos


def test_empty_oos_dataset_fails_closed(tmp_path):
    p=tmp_path/"polls.csv"
    p.write_text("election,election_date,party,poll,actual,house,field_end,source,poll_id\n")
    with pytest.raises(ValueError, match="vacío"):
        load_poll_observations(p)


def test_oos_requires_two_elections(tmp_path):
    p=tmp_path/"polls.csv"
    p.write_text(
        "election,election_date,party,poll,actual,house,field_end,source,poll_id\n"
        "2023,2023-07-23,A,0.4,0.4,H,2023-07-20,S,P1\n"
    )
    rows=load_poll_observations(p)
    with pytest.raises(ValueError, match="dos elecciones"):
        run_oos(rows)
