"""Uji run ulang dan muat ulang karantina (Q6, Q12) pada SALINAN database; production.duckdb asli tidak diubah.
  A. Run ke-3 pada file yang sama: isi tabel tidak berubah (idempotent).
  B. Sebagian data production_log hilang (100 baris dihapus): run ulang memulihkan tepat 100 baris itu.
  C. Perbaikan karantina: 5 perbaikan yang salah ditolak lagi; 240 baris yang bisa diperbaiki dimuat ulang, baris lain tidak berubah.
Hasil: results/2-analysis/rerun_test.csv. Jalankan dari folder project/: python code/2-analysis/python/06_rerun_and_reload.py"""
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import duckdb  # noqa: E402
import pandas as pd  # noqa: E402

from common import DB_PATH, LOG_DIR, MAPPING_YML, RES_ANALYSIS, chdir_root  # noqa: E402
from etl.extract import load_config  # noqa: E402
from etl.validate_load import reload_fixed, run_etl, scalar  # noqa: E402
from truth_map import file_maps, load_issues, load_truth  # noqa: E402

chdir_root()
cfg = load_config(MAPPING_YML)
files = sorted(LOG_DIR.glob("log_*.xlsx"))
tmp = Path(tempfile.mkdtemp()) / "copy.duckdb"
shutil.copy(DB_PATH, tmp)
con = duckdb.connect(str(tmp))
SNAP = {"stg_raw_rows": "source_file || row_no || template_version || raw_json", "rejected_rows": "source_file || row_no || rule_failed || coalesce(detail,'') || raw_value",
        "production_log": "CAST(date AS VARCHAR) || shift || station || model || operator_id || input_qty || ok_qty || ng_qty || source_file || row_no || coalesce(fixes,'')"}


def snap(table, where=""):
    return con.execute(f"SELECT count(*), md5(string_agg({SNAP[table]}, '|' ORDER BY {SNAP[table]})) FROM {table} {where}").fetchall()[0]


rows = []
add = lambda test, exp, act: rows.append(dict(test=test, expected=str(exp), actual=str(act), status="PASS" if str(exp) == str(act) else "FAIL"))
n0 = {t: snap(t) for t in SNAP}
nlog0 = scalar(con, "SELECT count(*) FROM etl_run_log")
r3 = run_etl(con, files, cfg)
add("A. Run ke-3: baris baru masuk production_log", 0, r3["rows_inserted"])
for t in SNAP:
    add(f"A. Run ke-3: isi tabel {t} (jumlah dan checksum) tidak berubah", n0[t], snap(t))
add("A. Run ke-3: baris etl_run_log bertambah satu", nlog0 + 1, scalar(con, "SELECT count(*) FROM etl_run_log"))
# B. sebagian data hilang
con.execute("CREATE TEMP TABLE hilang AS SELECT date, station, model, shift FROM production_log ORDER BY hash(source_file || row_no) LIMIT 100")
con.execute("DELETE FROM production_log USING hilang h WHERE production_log.date = h.date AND production_log.station = h.station AND production_log.model = h.model AND production_log.shift = h.shift")
add("B. 100 baris dihapus: production_log berkurang", n0["production_log"][0] - 100, scalar(con, "SELECT count(*) FROM production_log"))
rb = run_etl(con, files, cfg)
add("B. Run ulang memulihkan tepat 100 baris", 100, rb["rows_inserted"])
add("B. Isi production_log kembali sama (kecuali nomor run)", n0["production_log"], snap("production_log"))
# C. perbaikan karantina
truth, issues = load_truth(), load_issues()
maps = file_maps(issues)
rj = con.execute("SELECT DISTINCT r.source_file, r.row_no, s.seq FROM rejected_rows r JOIN stg_raw_rows s ON s.source_file = r.source_file AND s.row_no = r.row_no").df()
tk = truth.set_index(["file", "idx"])
fix, copies = [], 0
for r in rj.itertuples(index=False):
    idx, is_copy = maps[r.source_file][int(r.seq)]
    if is_copy:
        copies += 1
        continue
    t = tk.loc[(r.source_file, idx)]
    fix.append(dict(source_file=r.source_file, row_no=int(r.row_no), date=t.date, shift=t["shift"], model=t.model, operator_id=t.operator_id,
                    input_qty=int(t.input_qty), ok_qty=int(t.ok_qty), ng_qty=int(t.ng_qty)))
fix = pd.DataFrame(fix)
add("C. Baris karantina yang bisa diperbaiki (bukan salinan ganda)", 240, len(fix))
add("C. Salinan baris ganda (dibuang, tidak diperbaiki)", 60, copies)
before_hash, before_n = snap("production_log")[1], scalar(con, "SELECT count(*) FROM production_log")
wrong = fix.head(5).copy()
wrong["ok_qty"] += 1
w = reload_fixed(con, wrong, cfg)
add("C. 5 perbaikan yang salah (OK + NG tidak sama dengan input): dimuat", 0, w["reloaded"])
add("C. 5 perbaikan yang salah: ditolak lagi", 5, w["still_rejected"])
add("C. Isi production_log tidak berubah oleh perbaikan yang salah", before_hash, snap("production_log")[1])
orig_keys = con.execute("SELECT source_file, row_no FROM production_log").df()
h_before = con.execute("SELECT md5(string_agg(" + SNAP["production_log"] + ", '|' ORDER BY " + SNAP["production_log"] + ")) FROM production_log").fetchall()[0][0]
ok = reload_fixed(con, fix, cfg)
add("C. Perbaikan benar: baris dimuat ulang", 240, ok["reloaded"])
add("C. Perbaikan benar: baris masih ditolak", 0, ok["still_rejected"])
add("C. Baris production_log sesudah muat ulang", before_n + 240, scalar(con, "SELECT count(*) FROM production_log"))
con.register("ok_keys", orig_keys)
h_after = con.execute("SELECT md5(string_agg(" + SNAP["production_log"] + ", '|' ORDER BY " + SNAP["production_log"] + ")) FROM (SELECT p.* FROM production_log p JOIN ok_keys k ON k.source_file = p.source_file AND k.row_no = p.row_no)").fetchall()[0][0]
add("C. 6.960 baris yang sudah ada tidak berubah (checksum)", h_before, h_after)
add("C. rejected_rows.fixed_at terisi untuk baris yang diperbaiki", 240, scalar(con, "SELECT count(DISTINCT source_file || row_no) FROM rejected_rows WHERE fixed_at IS NOT NULL"))
add("C. Baris karantina yang tidak diperbaiki (salinan ganda) tetap tanpa fixed_at", 60, scalar(con, "SELECT count(DISTINCT source_file || row_no) FROM rejected_rows WHERE fixed_at IS NULL"))
# data akhir sama dengan data bersih asal (truth)
db = con.execute("SELECT CAST(date AS VARCHAR) AS date, station, model, shift, input_qty, ok_qty, ng_qty FROM production_log").df()
tt = truth[["date", "station", "model", "shift", "input_qty", "ok_qty", "ng_qty"]]
m = db.merge(tt, on=["date", "station", "model", "shift"], how="outer", suffixes=("_db", "_tr"), indicator=True)
same = int(((m._merge == "both") & (m.input_qty_db == m.input_qty_tr) & (m.ok_qty_db == m.ok_qty_tr) & (m.ng_qty_db == m.ng_qty_tr)).sum())
add("C. Setelah muat ulang: baris production_log yang sama persis dengan data bersih asal", len(tt), same)
add("C. Setelah muat ulang: baris tanpa pasangan di data bersih asal", 0, int((m._merge != "both").sum()))
con.close()
out = pd.DataFrame(rows)
out.to_csv(RES_ANALYSIS / "rerun_test.csv", index=False)
print(out.to_string(index=False))
assert (out.status == "PASS").all()
