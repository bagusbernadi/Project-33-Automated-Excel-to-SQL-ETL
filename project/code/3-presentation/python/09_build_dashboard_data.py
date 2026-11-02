"""Langkah 9: menyiapkan data ringkas untuk dashboard (baris = stasiun x model x bulan, plus ringkasan ETL dan kualitas data).
Sumber: CSV hasil analisis. Keluaran: results/3-presentation/dash_*.csv (di-commit supaya dashboard jalan tanpa database)."""
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402

C.chdir_root()
for src, dst in (("prod_station_model_month.csv", "dash_prod.csv"), ("dq_station.csv", "dash_dq_station.csv"), ("dq_month.csv", "dash_dq_month.csv"), ("issues_by_type.csv", "dash_issues.csv"),
                 ("impact_steps.csv", "dash_impact_steps.csv"), ("impact.csv", "dash_impact.csv"), ("etl_runs_summary.csv", "dash_runs.csv")):
    (C.RES_PRESENT / dst).write_bytes(C.result(src).read_bytes())
print("dashboard data ditulis:", sorted(p.name for p in C.RES_PRESENT.glob("dash_*.csv")))
