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

def test_http_health_and_custom_simulation_routes():
    import json
    from http.server import ThreadingHTTPServer
    from threading import Thread
    from urllib.request import Request, urlopen
    from scripts.demo_decision_server import Handler

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urlopen(base + "/api/health", timeout=5) as response:
            health = json.loads(response.read())
        assert health["status"] == "OK"
        with urlopen(base + "/api/candidates?region=Madrid", timeout=5) as response:
            catalogue = json.loads(response.read())
        assert catalogue["region"] == "Madrid"
        payload = json.dumps({
            "region": "Madrid",
            "label": "Coalición HTTP",
            "members": ["PARTIDO SOCIALISTA OBRERO ESPAÑOL - PSOE", "SUMAR - SUMAR"],
        }).encode()
        request = Request(base + "/api/simulate", data=payload, headers={"Content-Type":"application/json"}, method="POST")
        with urlopen(request, timeout=5) as response:
            result = json.loads(response.read())
        assert result["status"] == "OK"
        assert result["seat_delta"] == 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
