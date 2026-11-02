"""Mencocokkan hasil ETL dengan fakta yang ditanam generator (ground_truth) dan dengan data bersih asal (truth_production.csv).
Hasil: results/2-analysis/issue_recovery.csv (per jenis masalah tertanam) dan ground_truth_check.csv (5 fakta rancangan).
File ground truth hanya dibaca di sini, bukan di analisis. Jalankan dari folder project/: python code/2-analysis/python/08_ground_truth_check.py"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import duckdb  # noqa: E402
import pandas as pd  # noqa: E402

from common import DB_PATH, GROUND_TRUTH, RES_ANALYSIS, RES_PREP, chdir_root  # noqa: E402
from truth_map import file_maps, load_issues, load_truth  # noqa: E402

chdir_root()
con = duckdb.connect(str(DB_PATH), read_only=True)
truth, issues = load_truth(), load_issues()
maps = file_maps(issues)
gt = json.loads(GROUND_TRUTH.read_text(encoding="utf-8"))
stg = con.execute("SELECT source_file, row_no, seq, template_version, raw_json FROM stg_raw_rows").df()
rej = con.execute("SELECT source_file, row_no, rule_failed FROM rejected_rows").df()
prod = con.execute("SELECT CAST(date AS VARCHAR) AS date, shift, station, model, operator_id, input_qty, ok_qty, ng_qty, source_file, row_no, fixes FROM production_log").df()
con.close()
rules = rej.groupby(["source_file", "row_no"]).rule_failed.apply(set).to_dict()
loaded = prod.set_index(["source_file", "row_no"])
seq2row = stg.set_index(["source_file", "seq"]).row_no.to_dict()
tk = truth.set_index(["file", "idx"])
pos = {f: {(i, c): p for p, (i, c) in enumerate(m)} for f, m in maps.items()}
EXPECT = {"model_typo": ("dimuat dengan nilai benar", None), "text_qty": ("dimuat dengan nilai benar", None), "blank_cell": ("dikarantina R01", "R01"),
          "negative_qty": ("dikarantina R03", "R03"), "ok_ng_mismatch": ("dikarantina R04", "R04"), "formula_overwrite": ("dikarantina R04", "R04"),
          "duplicate_row": ("baris asli dimuat, salinan dikarantina R05", "R05")}


def same_as_truth(file, idx, rn):
    if (file, rn) not in loaded.index:
        return False
    a, t = loaded.loc[(file, rn)], tk.loc[(file, idx)]
    return (a.date == t.date and a["shift"] == t["shift"] and a.model == t.model and a.operator_id == t.operator_id and int(a.input_qty) == int(t.input_qty)
            and int(a.ok_qty) == int(t.ok_qty) and int(a.ng_qty) == int(t.ng_qty))


res = []
planted_idx = set(zip(issues.file, issues.body_row_index))
for kind, (action, rule) in EXPECT.items():
    sub = issues[issues.issue_type == kind]
    good = 0
    for r in sub.itertuples():
        rn = seq2row[(r.file, pos[r.file][(r.body_row_index, False)])]
        if kind == "duplicate_row":
            rn_copy = seq2row[(r.file, pos[r.file][(r.body_row_index, True)])]
            good += int(same_as_truth(r.file, r.body_row_index, rn) and rules.get((r.file, rn_copy)) == {"R05"})
        elif rule is None:
            good += int(same_as_truth(r.file, r.body_row_index, rn) and (r.file, rn) not in rules)
        else:
            good += int(rule in rules.get((r.file, rn), set()) and (r.file, rn) not in loaded.index)
    res.append(dict(jenis_masalah=kind, ditanam=len(sub), ditangani_benar=good, tindakan_diharapkan=action))
# baris tanpa masalah: harus dimuat dan sama persis dengan data bersih asal (tidak ada positif palsu)
fp = tot = 0
for f, m in maps.items():
    for p, (i, copy) in enumerate(m):
        if copy or (f, i) in planted_idx:
            continue
        tot += 1
        rn = seq2row[(f, p)]
        fp += int(not same_as_truth(f, i, rn))
res.append(dict(jenis_masalah="baris tanpa masalah (positif palsu)", ditanam=tot, ditangani_benar=tot - fp, tindakan_diharapkan="dimuat dengan nilai sama persis dengan data bersih asal"))
rec = pd.DataFrame(res)
rec["pct"] = rec.ditangani_benar / rec.ditanam
rec.to_csv(RES_ANALYSIS / "issue_recovery.csv", index=False)

# ---- lima fakta pada rancangan
inv = pd.read_csv(RES_PREP / "template_inventory.csv")
dtype = {"datetime": r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$", "dd/mm/yy": r"^\d{2}/\d{2}/\d{2}$", "dd-Mon-yy": r"^\d{2}-[A-Za-z]{3}-\d{2}$", "yyyy/mm/dd": r"^\d{4}/\d{2}/\d{2}$", "yyyy-mm-dd": r"^\d{4}-\d{2}-\d{2}$", "angka serial": r"^\d{5}(\.0)?$"}
dates = pd.Series([str(json.loads(x).get("date")) for x in stg.raw_json], dtype=object)
dfmt = {k: int(dates.str.match(v).sum()) for k, v in dtype.items()}
models = pd.Series([str(json.loads(x).get("model")) for x in stg.raw_json], dtype=object)
variants = sorted(set(models) - {"Basic", "Plus", "Pro", "None"})
n_var = int((~models.isin(["Basic", "Plus", "Pro", "None"])).sum())
rr = lambda n: int(rec[rec.jenis_masalah == n].ditangani_benar.iloc[0])
ngm = pd.read_csv(RES_ANALYSIS / "ng_station_month.csv")
rf = ngm[ngm.station == "Reflow Soldering"].set_index("month").ng_rate
jun_ratio = float(rf["2026-06"] / rf.drop("2026-06").mean())
tq = int(issues[issues.issue_type.isin(["blank_cell", "negative_qty", "ok_ng_mismatch", "formula_overwrite", "duplicate_row"])].shape[0])
n_rej = int(rej[["source_file", "row_no"]].drop_duplicates().shape[0])
n_rows = len(stg)
v = lambda n: int(inv[inv.template_version == n].iloc[0].files)
facts = [
    (1, "Tiga versi template, termasuk satu template khusus AOI Inspection",
     f"{inv.shape[0]} versi template ditemukan (v1 {v('v1')} file, v2 {v('v2')} file, v3 {v('v3')} file), semuanya terbaca otomatis dari pemetaan kolom. Versi berganti per bulan, bukan per stasiun, jadi tidak ada template khusus AOI Inspection",
     "Sebagian"),
    (2, "Format tanggal campuran: 02/08/2026, 2026-08-02, dan angka serial Excel",
     f"{sum(1 for k, x in dfmt.items() if x)} format tanggal ditemukan ({', '.join(f'{k}: {x}' for k, x in dfmt.items() if x)}); semua terbaca. Angka serial Excel tidak ada di data ({dfmt['angka serial']} baris)",
     "Sebagian"),
    (3, "Nama model beragam: Pro, PRO, pro, dan Model Pro",
     f"{n_var} baris bernama model tidak baku ({', '.join(repr(x) for x in variants)}), semuanya dinormalkan dengan benar ({rr('model_typo')} dari {int((issues.issue_type == 'model_typo').sum())} sama dengan data asal). Variasi Model Pro, pro tidak ada di data",
     "Sebagian"),
    (4, "Merged cell di judul, baris subtotal, dan baris kosong di tengah data",
     f"{int(inv.merged_cells.sum())} file dengan merged cell, {int(inv.summary_rows.sum())} baris TOTAL, {int(inv.blank_rows.sum())} baris kosong, dan {int(inv.title_rows.sum())} baris judul semuanya dilewati; 0 baris data hilang (rekonsiliasi 60 dari 60 file cocok)",
     "Sesuai"),
    (5, "Sekitar 2 sampai 3% nilai tidak valid; NG Reflow Soldering naik di bulan ke-4",
     f"{len(issues)} masalah tertanam ({len(issues) / n_rows * 100:.1f}% baris), {tq} perlu karantina dan semuanya ditemukan ({n_rej} baris ditolak = {n_rej / n_rows * 100:.1f}%); 120 masalah format diperbaiki. "
     f"Kenaikan NG Reflow bulan ke-4 tidak ditanam: rate Juni {jun_ratio:.2f} kali rata-rata lima bulan lain",
     "Sebagian"),
]
gtc = pd.DataFrame(facts, columns=["fact_no", "fakta", "ditemukan", "hasil"])
gtc.to_csv(RES_ANALYSIS / "ground_truth_check.csv", index=False)
print(rec.to_string(index=False)); print(gtc[["fact_no", "hasil"]].to_string(index=False))
for r in facts:
    print(r[0], r[2])
assert (rec.ditangani_benar == rec.ditanam).all()
