"""Cek silang: hasil SQL (CSV di results/2-analysis) dihitung ulang dengan pandas dari tabel DuckDB. Hasil: results/2-analysis/crosscheck.csv (Q4, Q7, Q8, Q1 sampai Q3).
Jalankan dari folder project/: python code/2-analysis/python/04_crosscheck.py"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import duckdb  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from common import DB_PATH, RES_ANALYSIS, chdir_root  # noqa: E402

chdir_root()
con = duckdb.connect(str(DB_PATH), read_only=True)
prod = con.execute("SELECT * FROM production_log").df()
rej = con.execute("SELECT * FROM rejected_rows").df()
stg = con.execute("SELECT source_file, row_no, template_version FROM stg_raw_rows").df()
con.close()
R = lambda n: pd.read_csv(RES_ANALYSIS / n)
rows = []


def cmp(name, sql_df, pd_df, keys, cols, tol=1e-6):
    a = sql_df.sort_values(keys).reset_index(drop=True)
    b = pd_df.sort_values(keys).reset_index(drop=True)
    ok = len(a) == len(b) and all((a[k].astype(str) == b[k].astype(str)).all() for k in keys)
    diff = max((np.abs(a[c].astype(float) - b[c].astype(float)).max() for c in cols), default=0) if ok else float("nan")
    rows.append(dict(check=name, n_compared=len(a) * len(cols), max_abs_diff=diff, status="PASS" if ok and diff <= tol else "FAIL"))


prod["month"] = pd.to_datetime(prod.date).dt.strftime("%Y-%m")
g = prod.groupby(["station", "model", "month"], as_index=False).agg(input_qty=("input_qty", "sum"), ok_qty=("ok_qty", "sum"), ng_qty=("ng_qty", "sum"), n_rows=("input_qty", "size"))
g["yield"] = g.ok_qty / g.input_qty
g["ng_rate"] = g.ng_qty / g.input_qty
cmp("Output, yield, NG per stasiun, model, bulan (Q7)", R("prod_station_model_month.csv"), g, ["station", "model", "month"], ["input_qty", "ok_qty", "ng_qty", "yield", "ng_rate", "n_rows"])
s = prod.groupby("station", as_index=False).agg(input_qty=("input_qty", "sum"), ok_qty=("ok_qty", "sum"), ng_qty=("ng_qty", "sum"))
s["yield"] = s.ok_qty / s.input_qty
cmp("Yield per stasiun (Q7)", R("prod_station.csv"), s, ["station"], ["input_qty", "ok_qty", "ng_qty", "yield"])
m = prod.groupby("model", as_index=False).agg(input_qty=("input_qty", "sum"), ok_qty=("ok_qty", "sum"), ng_qty=("ng_qty", "sum"))
m["yield"] = m.ok_qty / m.input_qty
cmp("Yield per model (Q7)", R("prod_model.csv"), m, ["model"], ["input_qty", "ok_qty", "ng_qty", "yield"])
mo = prod.groupby("month", as_index=False).agg(input_qty=("input_qty", "sum"), ok_qty=("ok_qty", "sum"), ng_qty=("ng_qty", "sum"))
mo["yield"] = mo.ok_qty / mo.input_qty
cmp("Yield per bulan (Q7)", R("prod_month.csv"), mo, ["month"], ["input_qty", "ok_qty", "ng_qty", "yield"])
d = prod.groupby("date", as_index=False).agg(input_qty=("input_qty", "sum"), ok_qty=("ok_qty", "sum"), ng_qty=("ng_qty", "sum")).sort_values("date")
d["yield"] = d.ok_qty / d.input_qty
d["ng_rate"] = d.ng_qty / d.input_qty
d["yield_ma7"] = d["yield"].rolling(7, min_periods=1).mean()
d["ng_rate_ma7"] = d["ng_rate"].rolling(7, min_periods=1).mean()
d["date"] = d.date.astype(str)
cmp("Tren harian dan rata-rata bergerak 7 hari (Q8)", R("daily_trend.csv"), d, ["date"], ["input_qty", "ok_qty", "ng_qty", "yield", "ng_rate", "yield_ma7", "ng_rate_ma7"])
# kualitas data: status tiap baris data dari tabel staging
rej_rows = set(zip(rej.source_file, rej.row_no))
loaded = prod.set_index(["source_file", "row_no"]).fixes
st = stg.copy()
st["status"] = [("ditolak" if (f, r) in rej_rows else ("bersih" if pd.isna(loaded.get((f, r))) else "diperbaiki format")) for f, r in zip(st.source_file, st.row_no)]
st["stn_no"] = st.source_file.str.extract(r"log_(\d\d)_")[0]
st["month"] = st.source_file.str.extract(r"(\d{4}-\d{2})\.xlsx")[0]
ct = pd.crosstab(st.source_file, st.status).reset_index()
for c in ("bersih", "diperbaiki format", "ditolak"):
    ct[c] = ct.get(c, 0)
ct["rows_total"] = ct[["bersih", "diperbaiki format", "ditolak"]].sum(axis=1)
ct["dq_score"] = ct["bersih"] / ct.rows_total * 100
f = R("dq_file.csv")
cmp("Data quality score per file (Q2)", f[["source_file", "rows_total", "rows_clean", "rows_fixed", "rows_rejected", "dq_score"]],
    ct.rename(columns={"bersih": "rows_clean", "diperbaiki format": "rows_fixed", "ditolak": "rows_rejected"})[["source_file", "rows_total", "rows_clean", "rows_fixed", "rows_rejected", "dq_score"]],
    ["source_file"], ["rows_total", "rows_clean", "rows_fixed", "rows_rejected", "dq_score"])
mm = st.groupby("month").status.value_counts().unstack(fill_value=0).reset_index()
mm["rows_total"] = mm[["bersih", "diperbaiki format", "ditolak"]].sum(axis=1)
mm["dq_score"] = mm["bersih"] / mm.rows_total * 100
cmp("Data quality score per bulan (Q3)", R("dq_month.csv")[["month", "rows_total", "dq_score"]], mm[["month", "rows_total", "dq_score"]], ["month"], ["rows_total", "dq_score"])
ij = R("issues_by_type.csv")
n_rej_by_rule = rej.groupby("rule_failed").apply(lambda x: len(x[["source_file", "row_no"]].drop_duplicates()), include_groups=False).rename("baris").reset_index().rename(columns={"rule_failed": "kode"})
cmp("Baris ditolak per aturan (Q1)", ij[ij.kode.str.startswith("R")][["kode", "baris"]], n_rej_by_rule, ["kode"], ["baris"])
runs = R("etl_runs_summary.csv")
rows.append(dict(check="Jumlah baris dimuat + ditolak = baris dibaca, tiap run (Q4)", n_compared=len(runs) * 2, max_abs_diff=float(np.abs(runs.rows_valid + runs.rows_rejected - runs.rows_read).max()),
                 status="PASS" if ((runs.rows_valid + runs.rows_rejected) == runs.rows_read).all() else "FAIL"))
rows.append(dict(check="Baris production_log = baris staging - baris ditolak", n_compared=1, max_abs_diff=float(abs(len(prod) - (len(stg) - len(rej_rows)))),
                 status="PASS" if len(prod) == len(stg) - len(rej_rows) else "FAIL"))
out = pd.DataFrame(rows)
out["max_abs_diff"] = out.max_abs_diff.round(10)
out.to_csv(RES_ANALYSIS / "crosscheck.csv", index=False)
print(out.to_string(index=False))
assert (out.status == "PASS").all()
