from src.coalition_matrix import load_2023_matrix


def test_2023_matrix_is_complete_and_sums_to_congress():
    m=load_2023_matrix()
    assert len(m["seats"]) == 52
    assert sum(m["seats"].values()) == 350
    assert m["seats"]["Asturias"] == 7
    assert m["seats"]["Ceuta"] == 1
    assert m["seats"]["Melilla"] == 1
