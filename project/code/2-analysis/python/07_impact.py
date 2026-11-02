"""Dampak (Q5, Q9, Q10): durasi run ETL (terukur), jam kerja yang dihemat per tahun, dan waktu tunggu laporan. Semua angka waktu manual adalah asumsi (estimated).
Rumus Q9: (menit manual - menit ETL) x laporan per tahun / 60. Parameter di common.py dan docs/definitions.md.
Jalankan dari folder project/: python code/2-analysis/python/07_impact.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import pandas as pd  # noqa: E402

from common import ETL_WAIT_HOURS, MANUAL_STEPS, MANUAL_WAIT_HOURS, REPORTS_PER_MONTH, REPORTS_SCENARIOS, RES_ANALYSIS, chdir_root  # noqa: E402

chdir_root()
runs = pd.read_csv(RES_ANALYSIS / "etl_runs_summary.csv")
dur = float(runs.duration_s.max())                                  # run paling lambat dipakai (konservatif)
steps = pd.DataFrame(MANUAL_STEPS, columns=["langkah", "menit_manual", "menit_setelah_etl"])
steps["menit_dihemat"] = steps.menit_manual - steps.menit_setelah_etl
steps.to_csv(RES_ANALYSIS / "impact_steps.csv", index=False)
manual_min = float(steps.menit_manual.sum())
etl_min = float(steps.menit_setelah_etl.sum()) + dur / 60            # menit tinjau karantina dan cek laporan + durasi run terukur
rows = []
for n in REPORTS_SCENARIOS:
    rows.append(dict(laporan_per_bulan=n, laporan_per_tahun=n * 12, menit_manual=manual_min, menit_etl=round(etl_min, 2),
                     jam_dihemat_per_tahun=round((manual_min - etl_min) * n * 12 / 60, 1), dipakai="ya" if n == REPORTS_PER_MONTH else "tidak"))
pd.DataFrame(rows).to_csv(RES_ANALYSIS / "impact.csv", index=False)
wait = pd.DataFrame([dict(kondisi="Manual (asumsi)", jam=MANUAL_WAIT_HOURS), dict(kondisi="Setelah ETL (asumsi + durasi run terukur)", jam=round(ETL_WAIT_HOURS + dur / 3600, 4))])
wait["pengurangan"] = 1 - wait.jam / MANUAL_WAIT_HOURS
wait.to_csv(RES_ANALYSIS / "wait_time.csv", index=False)
print(pd.DataFrame(rows).to_string(index=False)); print(wait.to_string(index=False)); print("durasi run terlama (detik):", dur, "| < 60 detik:", dur < 60)
