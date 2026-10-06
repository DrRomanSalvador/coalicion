from __future__ import annotations
from pathlib import Path
import hashlib
import json
import pandas as pd

ROOT = Path(".audit_2023")
XLSX = ROOT / "Elecciones-Congreso.xlsx"

def norm(x):
    return "" if pd.isna(x) else str(x).strip().upper()

def main():
    if not XLSX.exists():
        raise SystemExit("Falta el XLSX oficial")

    sha = hashlib.sha256(XLSX.read_bytes()).hexdigest()
    sheets = pd.read_excel(XLSX, sheet_name=None, header=None, dtype=object)

    report = {
        "source": str(XLSX),
        "sha256": sha,
        "sheets": {},
    }

    for name, df in sheets.items():
        rows = []
        for i in range(min(len(df), 100)):
            vals = [norm(v) for v in df.iloc[i].tolist()]
            if any("2023" in v for v in vals):
                rows.append({"row": i + 1, "values": vals[:20]})
        report["sheets"][name] = {
            "rows": int(len(df)),
            "columns": int(len(df.columns)),
            "2023_markers": rows[:10],
        }

    (ROOT / "workbook_structure.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    with (ROOT / "workbook_structure.txt").open("w", encoding="utf-8") as f:
        for name, info in report["sheets"].items():
            f.write(f"\n=== {name} ===\n")
            f.write(f"rows={info['rows']} columns={info['columns']}\n")
            for row in info["2023_markers"]:
                f.write(f"row={row['row']} values={row['values']}\n")

    print(json.dumps(report, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
