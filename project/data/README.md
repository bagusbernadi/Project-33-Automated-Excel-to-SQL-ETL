# Data simulasi

- Versi data: v1
- Tanggal dibuat: 28 Okt 2026
- Seed: 33260302
- Data tidak disimpan di repo. Dibuat ulang (hasil identik) dengan:

```
pip install -r requirements.txt
cd code/1-data-preparation/python && python 01_generate_messy_logs.py
```

- Hasil di `data/raw/` (tidak di-commit): `logs/` (60 file Excel log, 10 stasiun x 6 bulan), `truth_production.csv` (7.200 baris data bersih), `ground_truth_issues.csv`, `ground_truth.json`. File ground truth hanya dibaca skrip validasi (`08_ground_truth_check.py`), tidak oleh ETL.
- `reference/column_mapping.yml`: pemetaan kolom per versi template, daftar stasiun, format tanggal, dan alias model.
- Uji determinisme: dijalankan 2x, SHA-256 semua berkas identik. Daftar hash ada di repo DataCenter, `simulasi/fingerprints/project-33.sha256`.
