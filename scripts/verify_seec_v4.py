from pathlib import Path

def check():
    e=Path("src/electoral.py").read_text()
    errors=[]
    if "sum(votes.values())+blank_votes" not in e: errors.append("validos")
    if 'special in {"Ceuta","Melilla"}' not in e: errors.append("ceuta")
    h=Path("data/historico_elecciones_generales.csv").read_text()
    if "2019A" not in h: errors.append("2019A")
    if "2019N" not in h: errors.append("2019N")
    if "EMPATE_ABSOLUTO_PENDIENTE" not in e: errors.append("empate")
    return errors

if __name__=="__main__":
    err=check()
    print({"status":"PASS" if not err else "FAIL","errors":err})
    raise SystemExit(bool(err))
