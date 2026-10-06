from src.reconciliation import reconcile
def test_exact_match(): assert reconcile({("2023","Madrid"):100},{("2023","Madrid"):100}).status=="PASS"
def test_difference_fails(): assert reconcile({("2023","Madrid"):100},{("2023","Madrid"):101}).status=="FAIL"
