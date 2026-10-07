from src.neutral_coalition import calculate_coalition, enumerate_coalitions

def dataset():
    return ({"A":{"X":600,"Y":250,"Z":150},"B":{"X":500,"Y":300,"Z":200}},
            {"A":3,"B":3},{"A":1000,"B":1000},{},{})

def test_missing_member_is_zero():
    v,s,valid,special,blank=dataset()
    r=calculate_coalition(v,s,valid,("X","Y","NOT_PRESENT"),special,blank)
    assert r.separate_seats==6 and r.coalition_seats==6

def test_delta_is_sum_of_constituency_deltas():
    v,s,valid,special,blank=dataset()
    r=calculate_coalition(v,s,valid,("X","Y"),special,blank)
    assert r.delta==sum(r.delta_by_constituency.values())

def test_label_permutation_preserves_math():
    v,s,valid,special,blank=dataset()
    r1=calculate_coalition(v,s,valid,("X","Y"),special,blank)
    perm={c:{"P" if p=="X" else "Q" if p=="Y" else p:v for p,v in row.items()} for c,row in v.items()}
    r2=calculate_coalition(perm,s,valid,("P","Q"),special,blank)
    assert (r1.separate_seats,r1.coalition_seats,r1.delta)==(r2.separate_seats,r2.coalition_seats,r2.delta)

def test_enumerates_all_pairs_and_triple():
    assert list(enumerate_coalitions(["C","A","B"]))==[("A","B"),("A","C"),("B","C"),("A","B","C")]
