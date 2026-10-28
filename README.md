[← Back to portfolio](https://bagusbernadi.github.io/)

# Project 33: Automated ETL: Excel Log → SQL Database

**Status: Design (rancangan).**

**Tujuan:** Membangun pipeline ETL otomatis yang membaca log Excel operator yang berantakan, membersihkan dan memvalidasinya, lalu memuatnya ke database SQL, untuk mengukur seberapa banyak data yang bermasalah dan berapa jam kerja yang bisa dihemat.

Halaman rancangan: https://bagusbernadi.github.io/Project-33-Automated-Excel-to-SQL-ETL/

| | |
|---|---|
| Kategori | Manufaktur (perakitan smartphone) |
| Tingkat | Sulit |
| Data | Data simulasi log Excel operator yang berantakan |
| Tools | Python (pandas, openpyxl, pytest), DuckDB + SQL, Pandera (opsional), GitHub Actions, Streamlit + Plotly, Excel |

## 1. Problem
Bagaimana mengubah log operator yang berantakan menjadi data siap analisis?

## 2. Data
- Data simulasi buatan sendiri, dibuat oleh `scripts/generate_messy_logs.py` (Versi: v1; Tanggal dibuat: 28 Okt 2026; Seed: 33260302).
- 10 stasiun perakitan smartphone, 3 model (Basic, Plus, Pro), 2 shift, ±6 bulan, ±60 file Excel dengan 3 versi template. Perkiraan ±7.000 baris produksi.
- Tidak memakai data perusahaan.

## 3. Analysis
Belum dikerjakan. Rencana langkah ada di bagian Work Plan pada halaman rancangan.

## 4. Recommendation
Belum dikerjakan.

## 5. Impact
Belum dikerjakan. Angka dampak nanti diberi label `estimated` / `simulated`.

## Batasan yang sudah diketahui
- Log Excel di lapangan bisa lebih beragam dari simulasi.
- Baris bermasalah dikarantina, tidak diperbaiki otomatis.
- Menit per laporan sebelum ETL adalah asumsi; jam dihemat diberi label estimated.
- Pola belum tentu penyebab; pengujian statistik di Project 29.

## Struktur repository
```
index.html          # halaman rancangan (GitHub Pages)
README.md
etl/                # (rencana) extract, transform, validate & load
config/             # (rencana) pemetaan kolom per template
scripts/            # (rencana) generator log Excel berantakan
tests/              # (rencana) unit test dan rekonsiliasi
sql/                # (rencana) query analitik
dashboard/          # (rencana) laporan otomatis
```
