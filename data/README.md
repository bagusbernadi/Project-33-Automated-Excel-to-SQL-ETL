# Data simulasi

- Versi data: v1
- Tanggal dibuat: 28 Okt 2026
- Seed: 33260302
- Data tidak disimpan di repo. Dibuat ulang (hasil identik) dengan:

```
pip install numpy pandas openpyxl Faker reportlab Pillow   # sesuai impor skrip
python scripts/generate_messy_logs.py
```

- Hasil di `data/sim/`: 60 file Excel log (10 stasiun x 6 bulan), `truth_production.csv` (7.200 baris), `ground_truth_issues.csv`, `ground_truth.json`.
- Uji determinisme: dijalankan 2x, SHA-256 semua berkas identik. Daftar hash ada di repo DataCenter, `simulasi/fingerprints/project-33.sha256`.
