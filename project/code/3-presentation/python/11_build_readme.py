"""Membuat README.md di root repo; semua angka dibaca dari CSV hasil."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import ROOT, result  # noqa: E402

R = lambda n: pd.read_csv(result(n))
f = lambda v, d=1: f"{v:.{d}f}".replace(".", ",")
n = lambda v: f"{int(round(v)):,}".replace(",", ".")

runs, iss, rec, gtc, imp = R("etl_runs_summary.csv"), R("issues_by_type.csv"), R("issue_recovery.csv"), R("ground_truth_check.csv"), R("impact.csv")
cx, rc, rx, rr, wt = R("crosscheck.csv"), R("reconciliation.csv"), R("reconciliation_excel.csv"), R("rerun_test.csv"), R("wait_time.csv")
r1, r2 = runs.iloc[0], runs.iloc[1]
ip = imp[imp.dipakai == "ya"].iloc[0]
ok = lambda d: int((d.status == "PASS").sum())
real = rec[~rec.jenis_masalah.str.startswith("baris tanpa")]
clean = rec[rec.jenis_masalah.str.startswith("baris tanpa")].iloc[0]
n_sebagian = int((gtc.hasil == "Sebagian").sum())

md = f"""[← Back to portfolio](https://bagusbernadi.github.io/)

# Project 33: Automated ETL: Excel Log → SQL Database

**Status: Selesai di branch `project-33-build` (menunggu review sebelum digabung ke `main`).**

Halaman rancangan dan Report: https://bagusbernadi.github.io/Project-33-Automated-Excel-to-SQL-ETL/

| | |
|---|---|
| Kategori | Manufaktur (perakitan smartphone) |
| Tingkat | Sulit |
| Data | Data simulasi log Excel operator yang berantakan (10 stasiun, 3 model, 2 shift, Mar–Agu 2026) |
| Tools | Python (pandas, openpyxl, pytest), DuckDB + SQL, Streamlit + Plotly, GitHub Actions, Excel (cek silang), Jupyter |

## 1. Problem

Bagaimana mengubah log operator yang berantakan menjadi data siap analisis, berapa banyak yang bermasalah, dan berapa jam kerja yang bisa dihemat? Jawaban per pertanyaan ada di tab Report pada halaman project.

## 2. Data

- Data simulasi buatan sendiri dengan seed tetap (`project/code/1-data-preparation/python/01_generate_messy_logs.py`); hasil identik setiap dijalankan. Bukan data perusahaan.
- {n(r1.files_read)} file Excel, 3 versi template (berganti per bulan), {n(r1.rows_read)} baris data.
- {n(real.ditanam.sum())} masalah ditanam (7 jenis); data bersih asalnya disimpan terpisah dan hanya dipakai untuk validasi.

## 3. Analysis

- Run pertama: {n(r1.rows_read)} baris dibaca, {n(r1.rows_inserted)} dimuat, {n(r1.rows_rejected)} dikarantina ({f(r1.reject_rate * 100)}%), {f(r1.duration_s)} detik. Run kedua memuat {n(r2.rows_inserted)} baris baru (idempotent).
- Semua {n(real.ditanam.sum())} masalah ditangani sesuai harapan ({n(real.ditangani_benar.sum())}/{n(real.ditanam.sum())}); {n(clean.ditangani_benar)} dari {n(clean.ditanam)} baris tanpa masalah dimuat persis sama dengan data bersih asal.
- Rekonsiliasi per file: {ok(rc)}/{len(rc)} PASS; cek silang pandas {ok(cx)}/{len(cx)} PASS; Excel {ok(rx)}/{len(rx)} PASS. Uji run ulang dan koreksi karantina: {ok(rr)}/{len(rr)} PASS.
- Penyimpangan dari rancangan: {n_sebagian} dari {len(gtc)} fakta yang direncanakan hanya sebagian terwujud di data simulasi (lihat tab Report, 7.6).

## 4. Recommendation

Jadikan ETL ini jalur standar masuknya log Excel: baris bermasalah dikarantina dan dikoreksi manusia, bukan diperbaiki diam-diam. Tambah template baru lewat `column_mapping.yml`, tanpa mengubah kode.

## 5. Impact

Estimated / simulated: waktu menyusun satu laporan turun dari {f(ip.menit_manual, 0)} menit (asumsi) menjadi {f(ip.menit_etl)} menit; pada {n(ip.laporan_per_bulan)} laporan per bulan, sekitar {n(ip.jam_dihemat_per_tahun)} jam per tahun. Waktu tunggu laporan turun dari {f(wt.jam[0], 0)} jam menjadi sekitar {f(wt.jam[1] * 60, 0)} menit (asumsi).

## Batasan

- Data simulasi: hasil membuktikan metode, bukan kondisi pabrik; log nyata bisa lebih beragam.
- Menit per langkah sebelum ETL adalah asumsi penyusun, bukan pengukuran.
- Cek silang Excel dihitung ulang oleh LibreOffice, bukan Microsoft Excel.
- Dashboard belum di-deploy; workflow GitHub Actions ditulis tetapi baru terbukti jalan setelah branch di-push.

## Menjalankan

```
pip install -r project/requirements.txt
cd project/code
python 1-data-preparation/python/01_generate_messy_logs.py
python 1-data-preparation/python/02_run_etl.py
for s in 03 04 05 06 07 08; do python 2-analysis/python/${{s}}_*.py; done
for s in 09 10 11; do python 3-presentation/python/${{s}}_*.py; done
cd .. && python -m pytest tests -q
streamlit run code/3-presentation/streamlit/app.py
python design-and-report/src/build_report.py   # dari root repo
```

## Struktur repository

```
index.html                 Pengalihan ke design-and-report/
.github/workflows/         ci.yml (test), daily_etl.yml (jadwal harian)
design-and-report/         Halaman Design dan Report (src/ berisi generator)
project/
  code/1-data-preparation  Generator, paket etl/, skema SQL, run ETL
  code/2-analysis          Views SQL, query, cek silang, rekonsiliasi, run ulang, dampak
  code/3-presentation      Dashboard data, notebook, README, Streamlit
  tests/                   pytest
  results/                 CSV hasil per tahap, reconciliation.xlsx, notebook
  docs/                    Aturan validasi, definisi, kamus data, inventaris template
  data/                    column_mapping.yml, README (data mentah tidak di-commit)
```
"""
(ROOT.parent / "README.md").write_text(md, encoding="utf-8")
print("README.md ditulis")
