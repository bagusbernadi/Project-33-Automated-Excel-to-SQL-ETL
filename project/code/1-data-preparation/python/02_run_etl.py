"""Menjalankan pipeline ETL: membaca 60 file Excel, merapikan, validasi, dan memuat ke production.duckdb.
Run 1 pada database kosong; run 2 pada file yang sama (uji idempotent, Q6). Ringkasan ke project/results/1-data-preparation/etl_runs.csv.
Jalankan dari folder project/: python code/1-data-preparation/python/02_run_etl.py [--runs N]"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import duckdb  # noqa: E402
import pandas as pd  # noqa: E402

from common import DB_PATH, LOG_DIR, MAPPING_YML, RES_PREP, SQL_PREP, chdir_root  # noqa: E402
from etl.extract import load_config  # noqa: E402
from etl.validate_load import ensure_schema, run_etl  # noqa: E402


def main(runs=2):
    chdir_root()
    cfg = load_config(MAPPING_YML)
    files = sorted(LOG_DIR.glob("log_*.xlsx"))
    assert len(files) == 60, f"diharapkan 60 file, ditemukan {len(files)}"
    if DB_PATH.exists():
        DB_PATH.unlink()
    con = duckdb.connect(str(DB_PATH))
    ensure_schema(con, SQL_PREP / "01_schema.sql")
    out = [run_etl(con, files, cfg) for _ in range(runs)]
    con.close()
    df = pd.DataFrame(out)
    df.to_csv(RES_PREP / "etl_runs.csv", index=False)
    print(df.to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=2)
    main(ap.parse_args().runs)
