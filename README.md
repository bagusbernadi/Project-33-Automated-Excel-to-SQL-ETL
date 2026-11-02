[← Back to portfolio](https://bagusbernadi.github.io/)

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
- 60 file Excel, 3 versi template (berganti per bulan), 7.260 baris data.
- 420 masalah ditanam (7 jenis); data bersih asalnya disimpan terpisah dan hanya dipakai untuk validasi.

## 3. Analysis

- Run pertama: 7.260 baris dibaca, 6.960 dimuat, 300 dikarantina (4,1%), 1,3 detik. Run kedua memuat 0 baris baru (idempotent).
- Semua 420 masalah ditangani sesuai harapan (420/420); 6.780 dari 6.780 baris tanpa masalah dimuat persis sama dengan data bersih asal.
- Rekonsiliasi per file: 60/60 PASS; cek silang pandas 10/10 PASS; Excel 241/241 PASS. Uji run ulang dan koreksi karantina: 21/21 PASS.
- Penyimpangan dari rancangan: 4 dari 5 fakta yang direncanakan hanya sebagian terwujud di data simulasi (lihat tab Report, 7.6).

## 4. Recommendation

Jadikan ETL ini jalur standar masuknya log Excel: baris bermasalah dikarantina dan dikoreksi manusia, bukan diperbaiki diam-diam. Tambah template baru lewat `column_mapping.yml`, tanpa mengubah kode.

## 5. Impact

Estimated / simulated: waktu menyusun satu laporan turun dari 170 menit (asumsi) menjadi 8,0 menit; pada 8 laporan per bulan, sekitar 259 jam per tahun. Waktu tunggu laporan turun dari 24 jam menjadi sekitar 15 menit (asumsi).

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
for s in 03 04 05 06 07 08; do python 2-analysis/python/${s}_*.py; done
for s in 09 10 11; do python 3-presentation/python/${s}_*.py; done
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
