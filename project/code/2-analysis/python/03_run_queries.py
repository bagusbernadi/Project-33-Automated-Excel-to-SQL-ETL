"""Menjalankan view SQL dan menyimpan hasilnya ke project/results/2-analysis/*.csv (Q1 sampai Q8) dan 1-data-preparation (inventaris template).
Jalankan dari folder project/: python code/2-analysis/python/03_run_queries.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import duckdb  # noqa: E402
import pandas as pd  # noqa: E402

from common import DB_PATH, LOG_DIR, MAPPING_YML, RES_ANALYSIS, RES_PREP, SQL_ANALYSIS, chdir_root  # noqa: E402
from etl.extract import extract_file, load_config  # noqa: E402

chdir_root()
con = duckdb.connect(str(DB_PATH))
con.execute((SQL_ANALYSIS / "03_views.sql").read_text(encoding="utf-8"))
Q = lambda sql: con.execute(sql).df()
def save(df, name, d=RES_ANALYSIS, nd=6):
    df = df.copy()
    num = df.select_dtypes("number").columns
    df[num] = df[num].round(nd)
    df.to_csv(d / name, index=False)

# ---- Q4/Q5/Q6: ringkasan run dibaca dari etl_run_log (durasi dibulatkan satu desimal; tidak ikut dibandingkan antar rerun)
runs = Q("SELECT run_id, files_read, rows_read, rows_skipped, rows_valid, rows_inserted, rows_rejected, duration_s FROM etl_run_log ORDER BY run_id")
runs["load_rate"] = runs.rows_valid / runs.rows_read
runs["reject_rate"] = runs.rows_rejected / runs.rows_read
runs["duration_s"] = runs.duration_s.round(1)
save(runs, "etl_runs_summary.csv")

# ---- Q1: jenis masalah (baris ditolak per aturan dan baris diperbaiki format per jenis perbaikan)
total = int(Q("SELECT count(*) AS n FROM v_data_rows").n[0])
rej = Q("SELECT rule_failed AS kode, count(DISTINCT source_file || '#' || row_no) AS baris FROM rejected_rows GROUP BY 1 ORDER BY 1")
labels = {"R01": "Kolom wajib kosong atau tidak terbaca", "R02": "Nilai di luar daftar", "R03": "Jumlah negatif", "R04": "OK + NG tidak sama dengan input", "R05": "Baris ganda (kunci tanggal, stasiun, model, shift)"}
rej["jenis"] = rej.kode.map(labels)
rej["perlakuan"] = "Dikarantina"
fx = Q("""SELECT f AS kode, count(*) AS baris FROM (SELECT unnest(string_split(fixes, ',')) AS f FROM production_log WHERE fixes IS NOT NULL) GROUP BY f ORDER BY f""")
fxl = {"model_dinormalkan": "Penulisan model tidak seragam", "satuan_angka_dibuang": "Angka bersatuan teks (mis. 480 pcs)"}
fx["jenis"] = fx.kode.map(fxl)
fx["perlakuan"] = "Diperbaiki format, dimuat"
issues = pd.concat([rej, fx], ignore_index=True)[["kode", "jenis", "perlakuan", "baris"]]
issues["pct_baris"] = issues.baris / total
issues = issues.sort_values("baris", ascending=False, kind="stable")
save(issues, "issues_by_type.csv")

# ---- Q2: data quality score per stasiun dan file (skor = baris bersih / baris data)
for name, view, key in (("dq_station.csv", "v_dq_station", "ord"), ("dq_file.csv", "v_dq_file", "source_file")):
    df = Q(f"SELECT * FROM {view} ORDER BY {key}")
    df["dq_score"] = df.rows_clean / df.rows_total * 100
    df["reject_rate"] = df.rows_rejected / df.rows_total
    save(df, name)
# ---- Q3: tren bulanan
dm = Q("SELECT * FROM v_dq_month ORDER BY month")
dm["dq_score"] = dm.rows_clean / dm.rows_total * 100
dm["reject_rate"] = dm.rows_rejected / dm.rows_total
save(dm, "dq_month.csv")
dtpl = Q("""SELECT template_version, count(*) AS rows_total, count(*) FILTER (WHERE status='ditolak') AS rows_rejected,
            count(*) FILTER (WHERE status='bersih') AS rows_clean FROM v_data_rows GROUP BY 1 ORDER BY 1""")
dtpl["dq_score"] = dtpl.rows_clean / dtpl.rows_total * 100
save(dtpl, "dq_template.csv")

# ---- Q7: output, yield, NG per stasiun, model, bulan (data bersih)
save(Q("SELECT station, model, month, input_qty, ok_qty, ng_qty, yield, ng_rate, n_rows FROM v_prod_month ORDER BY ord, model, month"), "prod_station_model_month.csv")
save(Q("""SELECT station, ord, sum(input_qty)::BIGINT AS input_qty, sum(ok_qty)::BIGINT AS ok_qty, sum(ng_qty)::BIGINT AS ng_qty, sum(ok_qty) * 1.0 / sum(input_qty)::BIGINT AS yield
          FROM v_prod_month GROUP BY station, ord ORDER BY ord"""), "prod_station.csv")
save(Q("""SELECT model, sum(input_qty)::BIGINT AS input_qty, sum(ok_qty)::BIGINT AS ok_qty, sum(ng_qty)::BIGINT AS ng_qty, sum(ok_qty) * 1.0 / sum(input_qty)::BIGINT AS yield
          FROM v_prod_month GROUP BY model ORDER BY model"""), "prod_model.csv")
save(Q("""SELECT month, sum(input_qty)::BIGINT AS input_qty, sum(ok_qty)::BIGINT AS ok_qty, sum(ng_qty)::BIGINT AS ng_qty, sum(ok_qty) * 1.0 / sum(input_qty)::BIGINT AS yield
          FROM v_prod_month GROUP BY month ORDER BY month"""), "prod_month.csv")
save(Q("""SELECT station, month, sum(ng_qty) * 1.0 / sum(input_qty)::BIGINT AS ng_rate, sum(input_qty)::BIGINT AS input_qty
          FROM v_prod_month GROUP BY station, ord, month ORDER BY ord, month"""), "ng_station_month.csv")

# ---- Q8: tren harian dan lonjakan (rata-rata bergerak 7 hari; lonjakan = NG rate harian stasiun lebih dari rata-rata + 3 simpangan baku stasiun itu)
save(Q("""SELECT date, input_qty, ok_qty, ng_qty, yield, ng_rate,
                 avg(yield) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS yield_ma7,
                 avg(ng_rate) OVER (ORDER BY date ROWS BETWEEN 6 PRECEDING AND CURRENT ROW) AS ng_rate_ma7
          FROM v_prod_daily ORDER BY date"""), "daily_trend.csv")
save(Q("""WITH s AS (SELECT station, ord, date, input_qty, ng_qty, ng_rate, avg(ng_rate) OVER (PARTITION BY station) AS mu, stddev_samp(ng_rate) OVER (PARTITION BY station) AS sd
                   FROM v_prod_daily_station)
          SELECT station, date, input_qty, ng_qty, ng_rate, mu AS mean_ng_rate, sd AS sd_ng_rate, (ng_rate - mu) / sd AS z
          FROM s WHERE ng_rate > mu + 3 * sd ORDER BY z DESC, date, station"""), "daily_spikes.csv")

# ---- inventaris template (Tahap A): dibaca ulang dari file Excel lewat modul extract
cfg = load_config(MAPPING_YML)
meta = [extract_file(f, cfg)[0] for f in sorted(LOG_DIR.glob("log_*.xlsx"))]
inv = pd.DataFrame(meta).groupby("template_version").agg(files=("source_file", "count"), data_rows=("n_data", "sum"), blank_rows=("n_blank", "sum"), summary_rows=("n_summary", "sum"),
                                                          title_rows=("n_title", "sum"), merged_cells=("merged_cells", "sum"), header_row=("header_row", "first")).reset_index()
save(inv, "template_inventory.csv", RES_PREP)
con.close()
print(runs.to_string(index=False)); print(issues.to_string(index=False)); print(dm.to_string(index=False)); print(inv.to_string(index=False))
