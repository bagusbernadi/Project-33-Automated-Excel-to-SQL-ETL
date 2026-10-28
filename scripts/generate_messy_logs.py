"""Project 33: log Excel operator yang berantakan (simulasi, perakitan smartphone), 3 versi template. Seed tetap.

60 file = 10 stasiun x 6 bulan; 120 hari kerja (20 per bulan) x 3 model x 2 shift = 7.200 baris produksi bersih.
Template v1 (bulan 1-2), v2 (bulan 3-4), v3 (bulan 5-6). Hasil (data/sim/): logs/*.xlsx, truth_production.csv (bersih),
ground_truth_issues.csv (masalah tertanam per file/baris), ground_truth.json.
Jalankan: python scripts/generate_messy_logs.py   (versi data: v1; butuh openpyxl)
"""
import io
import json
import re
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "sim"
SEED = 33260302
DATA_VERSION = "v1"
STATIONS = ["Solder Paste Printing", "Component Placement", "Reflow Soldering", "AOI Inspection",
            "Board Test (ICT)", "Screen Assembly", "Housing Assembly", "Final Inspection",
            "Functional Test", "Packaging"]
MODELS, SHIFTS = ["Basic", "Plus", "Pro"], ["Shift 1", "Shift 2"]
BASE_NG = [0.012, 0.011, 0.040, 0.008, 0.013, 0.010, 0.015, 0.012, 0.020, 0.003]
MODEL_F = {"Basic": 0.85, "Plus": 1.0, "Pro": 1.25}
QTY = {"Basic": 460, "Plus": 420, "Pro": 360}
MONTH_STARTS = ["2026-03-02", "2026-04-01", "2026-05-01", "2026-06-01", "2026-07-01", "2026-08-03"]
DAYS_PER_MONTH = 20
ISSUE_RATE = 0.06              # +-6% baris punya masalah (dikarantina atau diperbaiki otomatis oleh ETL)
rng = np.random.default_rng(SEED)


def normalize_zip(path):
    buf = io.BytesIO()
    with zipfile.ZipFile(path) as zin, zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zout:
        for name in sorted(zin.namelist()):
            zi = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0)); zi.compress_type = zipfile.ZIP_DEFLATED
            data = zin.read(name)
            if name == "docProps/core.xml":
                data = re.sub(rb"(<dcterms:(?:created|modified)[^>]*>)[^<]*", rb"\g<1>2026-01-01T00:00:00Z", data)
            zout.writestr(zi, data)
    Path(path).write_bytes(buf.getvalue())


def month_rows(si, mi):
    days = pd.bdate_range(MONTH_STARTS[mi], periods=DAYS_PER_MONTH)
    rows = []
    for day in days:
        for m in MODELS:
            for sh in SHIFTS:
                qin = int(round(QTY[m] * rng.normal(1, 0.05)))
                ng = int(rng.binomial(qin, min(BASE_NG[si] * MODEL_F[m] * float(np.exp(rng.normal(0, 0.15))), 0.5)))
                rows.append([day.date(), sh, STATIONS[si], m, f"OP{(si * 2 + SHIFTS.index(sh)) % 20 + 1:02d}", qin, qin - ng, ng])
    return pd.DataFrame(rows, columns=["date", "shift", "station", "model", "operator_id", "input_qty", "ok_qty", "ng_qty"])


OUT.mkdir(parents=True, exist_ok=True)
(OUT / "logs").mkdir(exist_ok=True)
truth, issues = [], []
for si, st in enumerate(STATIONS):
    for mi in range(6):
        tpl = mi // 2 + 1                                           # versi template 1, 2, 3
        df = month_rows(si, mi)
        df.insert(0, "file", f"log_{si + 1:02d}_{st.split()[0].lower()}_{MONTH_STARTS[mi][:7]}.xlsx")
        truth.append(df)
        fname = df["file"].iloc[0]
        body = df.drop(columns="file").astype(object).copy()
        n_issue = int(round(len(body) * ISSUE_RATE))
        pick = rng.permutation(len(body))[:n_issue]
        kinds = ["model_typo", "blank_cell", "text_qty", "negative_qty", "ok_ng_mismatch", "duplicate_row", "formula_overwrite"]
        dup = []
        for k, i in enumerate(pick):
            kind = kinds[k % len(kinds)]
            if kind == "model_typo": body.at[i, "model"] = {"Basic": "basik", "Plus": "plus ", "Pro": "PRO."}[body.at[i, "model"]]
            elif kind == "blank_cell": body.at[i, ["shift", "model", "ok_qty", "ng_qty"][int(rng.integers(0, 4))]] = None
            elif kind == "text_qty": body.at[i, "input_qty"] = f"{body.at[i, 'input_qty']} pcs"
            elif kind == "negative_qty": body.at[i, "ng_qty"] = -abs(int(body.at[i, "ng_qty"]) or 1)
            elif kind == "ok_ng_mismatch": body.at[i, "ok_qty"] = int(body.at[i, "ok_qty"]) + int(rng.integers(8, 40))
            elif kind == "duplicate_row": dup.append(i)
            else: body.at[i, "ok_qty"] = int(body.at[i, "input_qty"]) - int(body.at[i, "ng_qty"]) + 1     # sel rumus ditimpa angka
            issues.append([fname, int(i), kind])
        if dup:
            body = pd.concat([body, body.loc[dup]]).sort_index(kind="stable").reset_index(drop=True)
        wb = Workbook(); wb.properties.creator = "simulasi"
        ws = wb.active; ws.title = "Log"
        if tpl == 1:                       # judul 2 baris, header di baris 4
            ws["A1"] = f"LOG PRODUKSI - {st}"; ws["A2"] = "Bulan: " + MONTH_STARTS[mi][:7]
            ws.append([]); ws.append([]); hdr = ["Tanggal", "Shift", "Model", "Operator", "Input", "OK", "NG"]
            ws.append(hdr)
            for r in body.itertuples(index=False):
                ws.append([r.date, r.shift, r.model, r.operator_id, r.input_qty, r.ok_qty, r.ng_qty])
        elif tpl == 2:                     # header digabung, tanggal teks dd/mm/yy, kolom Catatan, baris kosong tiap minggu
            ws["A1"] = f"{st} - Laporan Output"; ws.merge_cells("A1:H1"); ws.append([])
            ws.append(["Tgl", "Shift", "Model", "Operator", "Input", "OK", "NG", "Catatan"])
            for n, r in enumerate(body.itertuples(index=False)):
                d = r.date.strftime("%d/%m/%y")
                ws.append([d, r.shift, r.model, r.operator_id, r.input_qty, r.ok_qty, r.ng_qty, "" if rng.random() > 0.05 else "cek ulang"])
                if (n + 1) % 30 == 0: ws.append([])
        else:                              # v3: satu sel "OK/NG" bergabung, tanggal campur format, total di akhir
            ws.append(["Date", "Shift", "Model", "Operator", "Input", "OK/NG"])
            for n, r in enumerate(body.itertuples(index=False)):
                d = [r.date.strftime("%d-%b-%y"), r.date.strftime("%Y/%m/%d"), r.date.isoformat()][n % 3]
                ok, ng = r.ok_qty, r.ng_qty
                ws.append([d, r.shift, r.model, r.operator_id, r.input_qty, f"{ok}/{ng}"])
            ws.append(["TOTAL", None, None, None, int(sum(int(v) for v in df["input_qty"])), None])
        wb.save(OUT / "logs" / fname); normalize_zip(OUT / "logs" / fname)

T = pd.concat(truth, ignore_index=True)
T.to_csv(OUT / "truth_production.csv", index=False)
pd.DataFrame(issues, columns=["file", "body_row_index", "issue_type"]).to_csv(OUT / "ground_truth_issues.csv", index=False)
(OUT / "ground_truth.json").write_text(json.dumps({
    "seed": SEED, "version": DATA_VERSION, "n_files": 60, "clean_rows": len(T), "n_issues": len(issues), "issue_rate": ISSUE_RATE,
    "templates": {"v1": "bulan 1-2: judul 2 baris, header baris 4, tanggal sebagai tanggal",
                  "v2": "bulan 3-4: header digabung, tanggal teks dd/mm/yy, kolom Catatan, baris kosong tiap 30 baris",
                  "v3": "bulan 5-6: kolom 'OK/NG' satu sel teks, tanggal campur format, baris TOTAL di akhir"},
    "issue_types": sorted(set(i[2] for i in issues))}, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"60 file, {len(T)} baris bersih, {len(issues)} masalah tertanam")
