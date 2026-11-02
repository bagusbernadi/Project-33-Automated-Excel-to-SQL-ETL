"""Langkah 10: membuat dan menjalankan notebook analisis (results/3-presentation/analysis.ipynb) dari CSV hasil."""
import sys
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402

M, K = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
cells = [
    M("# Project 33: Automated ETL Excel Log → SQL Database\n\nSemua tabel dibaca dari `results/` (hasil skrip ETL, SQL, dan Python). Data adalah simulasi buatan sendiri (60 file Excel, 3 versi template, Mar–Agu 2026)."),
    K("""from pathlib import Path
import pandas as pd, matplotlib.pyplot as plt
ROOT = Path.cwd()
while not (ROOT / 'results').exists():
    ROOT = ROOT.parent
R = lambda f: pd.read_csv(next(ROOT / 'results' / d / f for d in ('1-data-preparation', '2-analysis', '3-presentation') if (ROOT / 'results' / d / f).exists()))
pd.options.display.float_format = '{:.4f}'.format
plt.rcParams.update({'figure.figsize': (9, 3.6), 'axes.spines.top': False, 'axes.spines.right': False})"""),
    M("## Inventaris template\nTiga versi template berbeda baris judul, header, sel gabungan, baris kosong, dan baris total."),
    K("R('template_inventory.csv')"),
    M("## Hasil run ETL\nRun kedua memuat 0 baris baru (idempotent)."),
    K("R('etl_runs_summary.csv')"),
    M("## Jenis masalah dan perlakuannya"),
    K("R('issues_by_type.csv')"),
    K("R('issue_recovery.csv')"),
    M("## Kualitas data per stasiun dan bulan"),
    K("d = R('dq_station.csv'); plt.bar(d.station, d.dq_score, color='#1A73E8'); plt.xticks(rotation=40, ha='right'); plt.ylim(90, 100); plt.ylabel('DQ score (%)'); plt.show()"),
    K("R('dq_month.csv')"),
    M("## Produksi per stasiun dan tren harian"),
    K("R('prod_station.csv')"),
    K("t = R('daily_trend.csv'); x = pd.to_datetime(t.date); plt.plot(x, t.ng_rate * 100, color='#9AA0A6', lw=.8); plt.plot(x, t.ng_rate_ma7 * 100, color='#E8710A'); plt.ylabel('NG rate (%)'); plt.show(); R('daily_spikes.csv')"),
    M("## Cek silang dan rekonsiliasi"),
    K("a, b, c = R('crosscheck.csv'), R('reconciliation.csv'), R('reconciliation_excel.csv')\nprint(f'pandas: {(a.status == \"PASS\").sum()}/{len(a)} PASS; rekonsiliasi file: {(b.status == \"PASS\").sum()}/{len(b)} PASS; Excel: {(c.status == \"PASS\").sum()}/{len(c)} PASS')\nR('total_row_check.csv')"),
    M("## Uji run ulang"),
    K("R('rerun_test.csv')"),
    M("## Dampak waktu (estimated / simulated)"),
    K("display(R('impact_steps.csv')); display(R('impact.csv')); R('wait_time.csv')"),
    M("## Validasi: fakta yang ditanam generator"),
    K("R('ground_truth_check.csv')[['fact_no', 'fakta', 'ditemukan', 'hasil']]"),
]
nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}})
out = C.RES_PRESENT / "analysis.ipynb"
NotebookClient(nb, timeout=300, kernel_name="python3", resources={"metadata": {"path": str(C.ROOT)}}).execute()
nbf.write(nb, out)
errs = [o for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", []) if o.output_type == "error"]
print("notebook", out.name, len(nb.cells), "sel;", len(errs), "error")
assert not errs
