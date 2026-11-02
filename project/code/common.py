"""Pengaturan bersama untuk semua skrip. Semua jalur relatif terhadap folder project/."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # folder project/
DATA = ROOT / "data"
RAW_DIR = DATA / "raw"                                 # data simulasi mentah (tidak di-commit)
LOG_DIR = RAW_DIR / "logs"                             # 60 file Excel log (tidak di-commit)
REF_DIR = DATA / "reference"
MAPPING_YML = REF_DIR / "column_mapping.yml"
GROUND_TRUTH = RAW_DIR / "ground_truth.json"           # catatan pola ditanam; hanya dibaca skrip validasi
TRUTH_CSV = RAW_DIR / "truth_production.csv"           # data bersih sebelum dikotori; hanya dibaca skrip validasi
ISSUES_CSV = RAW_DIR / "ground_truth_issues.csv"
DB_PATH = ROOT / "production.duckdb"                   # tidak di-commit
CODE = ROOT / "code"
ETL_DIR = CODE / "1-data-preparation" / "python"       # berisi paket etl/
SQL_PREP = CODE / "1-data-preparation" / "sql"
SQL_ANALYSIS = CODE / "2-analysis" / "sql"
RES_PREP = ROOT / "results" / "1-data-preparation"
RES_ANALYSIS = ROOT / "results" / "2-analysis"
RES_PRESENT = ROOT / "results" / "3-presentation"
DOCS_DIR = ROOT / "docs"
for _d in (RES_PREP, RES_ANALYSIS, RES_PRESENT):        # folder hasil dibuat otomatis (folder kosong tidak ikut di-commit)
    _d.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ETL_DIR))                       # agar paket etl bisa di-import dari skrip mana pun

SEED = 33260302
MONTHS = ["2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08"]
MODELS, SHIFTS = ["Basic", "Plus", "Pro"], ["Shift 1", "Shift 2"]

# Asumsi waktu penyusunan laporan (estimated; lihat docs/definitions.md). Contoh angka pada simulasi Design Project: 170 menit manual, 8 menit setelah ETL.
MANUAL_STEPS = [("Kumpulkan file", 25, 1), ("Salin dan gabung", 40, 0), ("Rapikan format", 35, 0),
                ("Cek salah ketik", 30, 5), ("Hitung KPI", 20, 0), ("Buat grafik", 20, 2)]   # (langkah, menit manual, menit setelah ETL)
REPORTS_PER_MONTH = 8
REPORTS_SCENARIOS = [4, 8, 12]
MANUAL_WAIT_HOURS = 24.0        # asumsi: laporan manual siap sehari setelah data tersedia
ETL_WAIT_HOURS = 0.25           # asumsi: laporan ETL siap 15 menit setelah file masuk (jalankan ETL, tinjau karantina)


def result(name):
    """Cari CSV hasil di folder hasil per tahap."""
    for d in (RES_PREP, RES_ANALYSIS, RES_PRESENT):
        p = d / name
        if p.exists():
            return p
    raise FileNotFoundError(name)


def chdir_root():
    os.chdir(ROOT)
