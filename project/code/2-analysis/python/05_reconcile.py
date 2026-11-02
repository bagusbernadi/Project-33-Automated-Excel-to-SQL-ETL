"""Rekonsiliasi (Q11): total di file Excel asli = total database + total karantina, per file dan per kolom (input, OK, NG).
Pembaca file Excel di sini sengaja ditulis terpisah dari etl/extract.py (pandas, bukan openpyxl langsung) agar hasilnya pembanding yang independen.
Hasil: results/2-analysis/reconciliation.csv, reconciliation_excel.csv, total_row_check.csv, dan reconciliation.xlsx (rumus Excel, dihitung ulang oleh LibreOffice).
Jalankan dari folder project/: python code/2-analysis/python/05_reconcile.py"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import duckdb  # noqa: E402
import numpy as np  # noqa: E402
import openpyxl  # noqa: E402
import pandas as pd  # noqa: E402
from openpyxl.styles import Font, PatternFill  # noqa: E402

from common import DB_PATH, LOG_DIR, RES_ANALYSIS, chdir_root  # noqa: E402

chdir_root()
NUM = re.compile(r"^\s*(-?\d+)\s*(?:pcs)?\s*$", re.I)


def num(x):
    """Angka dari sel; 0 bila kosong atau bukan angka (jumlah yang tidak terbaca tidak bisa ikut dijumlah)."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return 0
    if isinstance(x, (int, float, np.integer, np.floating)):
        return int(x)
    m = NUM.match(str(x))
    return int(m.group(1)) if m else 0


def read_independent(path):
    """Membaca file dengan pandas: cari baris header (sel pertama Tanggal, Tgl, atau Date), buang baris kosong dan TOTAL."""
    raw = pd.read_excel(path, header=None, dtype=object)
    h = next(i for i in range(min(12, len(raw))) if str(raw.iat[i, 0]).strip().lower() in ("tanggal", "tgl", "date"))
    hdr = [str(c).strip() for c in raw.iloc[h]]
    body = raw.iloc[h + 1:].copy()
    body.columns = hdr
    body = body.dropna(how="all")
    is_total = body.iloc[:, 0].astype(str).str.strip().str.upper().eq("TOTAL")
    total_val = body[is_total]["Input"].iloc[0] if is_total.any() else None
    body = body[~is_total]
    inp = body["Input"].map(num)
    if "OK/NG" in body.columns:
        pr = body["OK/NG"].astype(str).str.split("/", n=1, expand=True)
        ok, ng = pr[0].map(num), pr[1].map(num)
    else:
        ok, ng = body["OK"].map(num), body["NG"].map(num)
    return dict(rows=len(body), input=int(inp.sum()), ok=int(ok.sum()), ng=int(ng.sum()), total_row=None if total_val is None else num(total_val))


ind = {p.name: read_independent(p) for p in sorted(LOG_DIR.glob("log_*.xlsx"))}
con = duckdb.connect(str(DB_PATH), read_only=True)
db = con.execute("SELECT source_file, count(*) AS rows, sum(input_qty)::BIGINT AS input, sum(ok_qty)::BIGINT AS ok, sum(ng_qty)::BIGINT AS ng FROM production_log GROUP BY 1").df().set_index("source_file")
rj = con.execute("SELECT DISTINCT source_file, row_no, raw_value FROM rejected_rows").df()
con.close()
q = {}
for f, grp in rj.groupby("source_file"):
    vals = [json.loads(v) for v in grp.raw_value]
    inp = sum(num(v.get("input_qty")) for v in vals)
    ok = sum(num(v.get("ok_qty")) if "ok_qty" in v else num(str(v.get("ok_ng", "")).split("/")[0]) for v in vals)
    ng = sum(num(v.get("ng_qty")) if "ng_qty" in v else (num(str(v.get("ok_ng", "")).split("/")[1]) if "/" in str(v.get("ok_ng", "")) else 0) for v in vals)
    q[f] = dict(rows=len(vals), input=inp, ok=ok, ng=ng)
rows = []
for f, a in ind.items():
    d = db.loc[f] if f in db.index else pd.Series(dict(rows=0, input=0, ok=0, ng=0))
    k = q.get(f, dict(rows=0, input=0, ok=0, ng=0))
    rows.append(dict(source_file=f, rows_file=a["rows"], rows_db=int(d["rows"]), rows_quarantine=k["rows"], input_file=a["input"], input_db=int(d["input"]), input_quarantine=k["input"],
                     ok_file=a["ok"], ok_db=int(d["ok"]), ok_quarantine=k["ok"], ng_file=a["ng"], ng_db=int(d["ng"]), ng_quarantine=k["ng"]))
rec = pd.DataFrame(rows)
for c in ("rows", "input", "ok", "ng"):
    rec[f"diff_{c}"] = rec[f"{c}_file"] - rec[f"{c}_db"] - rec[f"{c}_quarantine"]
rec["status"] = np.where((rec[[f"diff_{c}" for c in ("rows", "input", "ok", "ng")]] == 0).all(axis=1), "PASS", "BEDA")
rec.to_csv(RES_ANALYSIS / "reconciliation.csv", index=False)

# baris TOTAL pada template v3 vs jumlah baris data di file yang sama (informasi tambahan)
tr = pd.DataFrame([dict(source_file=f, total_row=a["total_row"], input_rows_in_file=a["input"]) for f, a in ind.items() if a["total_row"] is not None])
tr["selisih"] = tr.input_rows_in_file - tr.total_row
tr.to_csv(RES_ANALYSIS / "total_row_check.csv", index=False)

# ---- lembar Excel dengan rumus; dihitung ulang oleh LibreOffice
wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Rekonsiliasi"
head = ["File", "Baris file", "Baris database", "Baris karantina", "Selisih baris", "Input file", "Input database", "Input karantina", "Selisih input",
        "OK file", "OK database", "OK karantina", "Selisih OK", "NG file", "NG database", "NG karantina", "Selisih NG", "Status"]
ws.append(head)
for c in ws[1]:
    c.font, c.fill = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1A73E8")
for i, r in enumerate(rec.itertuples(index=False), start=2):
    ws.append([r.source_file, r.rows_file, r.rows_db, r.rows_quarantine, f"=B{i}-C{i}-D{i}", r.input_file, r.input_db, r.input_quarantine, f"=F{i}-G{i}-H{i}",
               r.ok_file, r.ok_db, r.ok_quarantine, f"=J{i}-K{i}-L{i}", r.ng_file, r.ng_db, r.ng_quarantine, f"=N{i}-O{i}-P{i}",
               f'=IF(AND(E{i}=0,I{i}=0,M{i}=0,Q{i}=0),"PASS","BEDA")'])
n = len(rec) + 1
ws.append(["TOTAL"] + [f"=SUM({chr(66 + j)}2:{chr(66 + j)}{n})" for j in range(16)] + [f'=IF(COUNTIF(R2:R{n},"PASS")={len(rec)},"PASS","BEDA")'])
for c in ws[n + 1]:
    c.font = Font(bold=True)
ws.column_dimensions["A"].width = 38
ws.freeze_panes = "B2"
tmp = Path(tempfile.mkdtemp())
src = tmp / "reconciliation.xlsx"
wb.save(src)
subprocess.run(["soffice", "--headless", "--calc", "--convert-to", "xlsx:Calc MS Excel 2007 XML", "--outdir", str(tmp / "out"), str(src)], check=True, capture_output=True, timeout=180)
shutil.copy(tmp / "out" / "reconciliation.xlsx", RES_ANALYSIS / "reconciliation.xlsx")
w2 = openpyxl.load_workbook(RES_ANALYSIS / "reconciliation.xlsx", data_only=True).active
xl = [[c.value for c in row] for row in w2.iter_rows(min_row=2, max_row=n)]
ex = []
for r, x in zip(rec.itertuples(index=False), xl):
    for col, name in ((4, "baris"), (8, "input"), (12, "OK"), (16, "NG")):
        ex.append(dict(source_file=r.source_file, kolom=name, selisih_excel=x[col], selisih_python=getattr(r, f"diff_{ {'baris': 'rows', 'input': 'input', 'OK': 'ok', 'NG': 'ng'}[name]}"),
                       status="PASS" if x[col] == getattr(r, f"diff_{ {'baris': 'rows', 'input': 'input', 'OK': 'ok', 'NG': 'ng'}[name]}") == 0 else "FAIL"))
tot = [c for c in [cell.value for cell in w2[n + 1]]]
ex.append(dict(source_file="TOTAL (semua file)", kolom="status akhir", selisih_excel=str(tot[17]), selisih_python="PASS" if (rec.status == "PASS").all() else "BEDA", status="PASS" if tot[17] == "PASS" and (rec.status == "PASS").all() else "FAIL"))
pd.DataFrame(ex).to_csv(RES_ANALYSIS / "reconciliation_excel.csv", index=False)
print(rec[["rows_file", "rows_db", "rows_quarantine", "input_file", "input_db", "input_quarantine"]].sum().to_string())
print(rec.status.value_counts().to_string(), "| Excel:", pd.DataFrame(ex).status.value_counts().to_dict(), "| selisih baris TOTAL v3:", tr.selisih.describe()[["min", "max"]].to_dict())
