from scripts.demo_decision_server import candidates_for, simulate_custom_coalition


def test_custom_simulation_conserves_votes_and_reports_limits():
    result = simulate_custom_coalition({
        "region": "Madrid",
        "label": "Coalición de prueba",
        "members": ["PARTIDO SOCIALISTA OBRERO ESPAÑOL - PSOE", "SUMAR - SUMAR"],
    })
    assert result["status"] == "OK"
    assert result["votes_conserved"] is True
    assert result["valid_votes_before"] == result["valid_votes_after"]
    assert result["seats_coalition"] == 17
    assert result["seats_separate_total"] == 16
    assert result["seat_delta"] == 1
    assert result["not_a_prediction"] is True
    assert result["official_certification"] == "NOT_INDEPENDENTLY_CERTIFIED"


def test_candidate_catalogue_is_grounded_in_canonical_matrix():
    result = candidates_for("Barcelona")
    assert result["schema"] == "COALICION_CUSTOM_CANDIDATES_V1"
    assert result["magnitude"] == 32
    assert result["candidates"]
    assert result["canonical_dataset_git_blob_sha1"]


def test_custom_simulation_rejects_duplicate_and_unknown_members():
    import pytest
    with pytest.raises(ValueError, match="duplicadas"):
        simulate_custom_coalition({"region":"Madrid","members":["A","A"]})
    with pytest.raises(ValueError, match="no encontradas"):
        simulate_custom_coalition({"region":"Madrid","members":["A","NO EXISTE"]})


def test_custom_simulation_requires_two_members_and_valid_region():
    import pytest
    with pytest.raises(ValueError, match="al menos dos"):
        simulate_custom_coalition({"region":"Madrid","members":["A"]})
    with pytest.raises(ValueError, match="Circunscripción"):
        simulate_custom_coalition({"region":"Sevilla","members":["A","B"]})
