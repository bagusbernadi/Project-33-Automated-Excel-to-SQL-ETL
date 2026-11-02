"""Membuat design-and-report/index.html (Report Project versi 2) dari page_v1.html dan CSV hasil.

- Pane Design diambil apa adanya dari page_v1.html (dicek identik).
- Semua angka di Report berasal dari project/results/*.csv lewat helper I/D/P (report_lib.py) dan diaudit di akhir.
Jalankan dari folder mana saja:  python design-and-report/src/build_report.py
"""
import re
import sys
from pathlib import Path

import duckdb
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "project" / "code"))
sys.path.insert(0, str(HERE))
from common import DB_PATH, RES_ANALYSIS, RES_PREP, RES_PRESENT, result  # noqa: E402
from report_lib import (BLUE, D, cs, GREY, HI, I, NO, OK, P, PART, SOFT, audit, bars, esc, gbars, hbars,  # noqa: E402
                        legend, lines, qa, table)

R = lambda n: pd.read_csv(result(n))
PRIO = {1: "Utama", 2: "Utama", 3: "Pendukung", 4: "Utama", 5: "Utama", 6: "Utama", 7: "Utama", 8: "Pendukung", 9: "Utama", 10: "Pendukung",
        11: "Utama", 12: "Pendukung", 13: "Tambahan"}
QT = {1: "Jenis masalah apa yang paling sering muncul di log Excel, dan berapa persen baris yang terdampak?",
      2: "Stasiun dan file mana yang paling berantakan?",
      3: "Apakah kualitas log membaik atau memburuk dari bulan ke bulan?",
      4: "Berapa persen baris yang berhasil dimuat otomatis, dan berapa yang masuk karantina?",
      5: "Berapa lama satu kali run ETL untuk semua file?",
      6: "Jika ETL dijalankan ulang, apakah hasilnya sama dan tidak ada data ganda?",
      7: "Berapa output, yield, dan NG per stasiun, model, dan bulan berdasarkan data yang sudah bersih?",
      8: "Bagaimana tren harian yield dan NG, dan adakah lonjakan?",
      9: "Berapa jam kerja penyusunan laporan yang bisa dihemat per tahun?",
      10: "Berapa lama waktu dari data tersedia sampai laporan siap, sebelum dan sesudah ETL?",
      11: "Apakah total input, OK, dan NG di database sama dengan total di file Excel asli?",
      12: "Apakah baris di karantina bisa diperbaiki lalu dimuat ulang tanpa merusak data lain?",
      13: "Bisakah ETL berjalan otomatis setiap hari saat file baru masuk?"}
WARN = set()      # pertanyaan yang dijawab dengan catatan (dipakai chip, ringkasan, dan tabel evaluasi)


def Q(n, ans, warn=False):
    if warn:
        WARN.add(n)
    return qa(f"Q{n}", QT[n], PRIO[n], ans, "Terjawab dengan catatan" if warn else "Terjawab", warn)


mk = lambda *a: "".join(a)
MONTH = {"01": "Jan", "02": "Feb", "03": "Mar", "04": "Apr", "05": "Mei", "06": "Jun", "07": "Jul", "08": "Agu", "09": "Sep", "10": "Okt"}
mlab = lambda m: MONTH[m[5:7]]
TGL = lambda s: f"{int(str(s)[8:10])} {MONTH[str(s)[5:7]]}"

# ---------------------------------------------------------------- data
runs, tinv = R("etl_runs_summary.csv"), R("template_inventory.csv")
iss, rec, gtc = R("issues_by_type.csv"), R("issue_recovery.csv"), R("ground_truth_check.csv")
dqs, dqf, dqm, dqt = R("dq_station.csv"), R("dq_file.csv"), R("dq_month.csv"), R("dq_template.csv")
pst, pmd, pmo, psm = R("prod_station.csv"), R("prod_model.csv"), R("prod_month.csv"), R("prod_station_model_month.csv")
ngm, dtr, dsp = R("ng_station_month.csv"), R("daily_trend.csv"), R("daily_spikes.csv")
cx, rc, rx, tr, rr = R("crosscheck.csv"), R("reconciliation.csv"), R("reconciliation_excel.csv"), R("total_row_check.csv"), R("rerun_test.csv")
imp, ist, wt = R("impact.csv"), R("impact_steps.csv"), R("wait_time.csv")
con = duckdb.connect(str(DB_PATH), read_only=True)
dbc = {t: con.execute(f"SELECT count(*) FROM {t}").fetchall()[0][0] for t in ("stg_raw_rows", "production_log", "rejected_rows", "etl_run_log")}
n_rej_rows = con.execute("SELECT count(DISTINCT source_file || '|' || row_no) FROM rejected_rows").fetchall()[0][0]
sample = con.execute("""SELECT s.source_file, s.row_no, s.template_version, s.raw_json, p.date, p.shift, p.model, p.input_qty, p.ok_qty, p.ng_qty
                        FROM stg_raw_rows s JOIN production_log p ON p.source_file = s.source_file AND p.row_no = s.row_no
                        WHERE s.source_file LIKE 'log_03_reflow_2026-0%' AND s.seq = 5 ORDER BY s.source_file""").fetchall()
con.close()

r1, r2 = runs.iloc[0], runs.iloc[1]
real = rec[~rec.jenis_masalah.str.startswith("baris tanpa")]
cleanrow = rec[rec.jenis_masalah.str.startswith("baris tanpa")].iloc[0]
n_issue, n_fixfmt = int(real.ditanam.sum()), int(real[real.tindakan_diharapkan.str.startswith("dimuat dengan")].ditanam.sum())
rows_read = int(r1.rows_read)
nfile, nsta = int(r1.files_read), len(dqs)
ip = imp[imp.dipakai == "ya"].iloc[0]
isc = imp.set_index("laporan_per_bulan")
nrule = int(iss[iss.perlakuan == "Dikarantina"].baris.sum())
iss_q = iss[iss.perlakuan == "Dikarantina"].set_index("kode")
iss_f = iss[iss.perlakuan != "Dikarantina"]
dq0 = dqs.iloc[0]
rpt = lambda p: rr[rr.test.str.startswith(p)]
okc = lambda d: int((d.status == "PASS").sum())
rec_tot = rc[["rows_file", "rows_db", "rows_quarantine", "input_file", "input_db", "input_quarantine", "ok_file", "ok_db", "ok_quarantine", "ng_file", "ng_db", "ng_quarantine"]].sum()
ps = pst.set_index("station")
low, high = pst.sort_values("yield").iloc[0], pst.sort_values("yield").iloc[-1]
tot_in, tot_ok, tot_ng = pst.input_qty.sum(), pst.ok_qty.sum(), pst.ng_qty.sum()
rf = ngm[ngm.station == "Reflow Soldering"].set_index("month").ng_rate
rf_other = rf.drop("2026-06")
tbl = ngm.pivot(index="station", columns="month", values="ng_rate")
tbl = tbl.loc[list(pst.station)]
gtm = gtc.set_index("fact_no")
npr = {k: sum(1 for v in PRIO.values() if v == k) for k in ("Utama", "Pendukung", "Tambahan")}
ver = dqt.set_index("template_version")
tv = tinv.set_index("template_version")
csum = lambda t: "; ".join(f"{k}: {t}" for k in ())

assert int(rec_tot.rows_file) == rows_read and (rc.status == "PASS").all() and (rx.status == "PASS").all() and (cx.status == "PASS").all() and (rr.status == "PASS").all()
assert (real.ditangani_benar == real.ditanam).all() and cleanrow.ditangani_benar == cleanrow.ditanam
assert gtc.hasil.tolist() == ["Sebagian", "Sebagian", "Sebagian", "Sesuai", "Sebagian"], gtc.hasil.tolist()
assert dqf.dq_score.nunique() == 1 and dqs.dq_score.nunique() == 1 and dqm.reject_rate.nunique() == 1          # kualitas seragam: dasar catatan Q2 dan Q3
assert r2.rows_inserted == 0 and r1.rows_inserted + r1.rows_rejected == r1.rows_valid + r1.rows_rejected and r1.duration_s < 60
assert dbc["production_log"] == r1.rows_inserted and n_rej_rows == r1.rows_rejected

# ---------------------------------------------------------------- 1. data
kp = lambda c, v, l, d: f'<div class="card kpi" style="--h:var(--{c}H)"><span class="v">{v}</span><span class="l">{l}</span><span class="d">{d}</span></div>'
rp1 = mk(
    '<div class="kpis">',
    kp("navy", I(nfile), "file Excel log", f"{I(nsta)} stasiun × {I(len(dqm))} bulan, 3 versi template. Sesuai perkiraan rancangan (±60)."),
    kp("amber", I(rows_read), "baris data dibaca", f"Tanpa judul, header, baris kosong, dan baris TOTAL ({I(r1.rows_skipped)} baris dilewati). Perkiraan rancangan ±7.000."),
    kp("teal", I(r1.rows_inserted), "baris dimuat ke production_log", f"{P(r1.load_rate)} dari baris data. Sisanya {I(r1.rows_rejected)} baris dikarantina."),
    kp("plum", I(n_issue), "masalah ditanam generator", f"{I(n_issue // 7)} untuk tiap dari 7 jenis ({P(n_issue / rows_read)} dari baris data). Semuanya ditangani sesuai harapan."),
    kp("rose", f"{r1.duration_s:.1f} dtk".replace(".", ","), "durasi satu run ETL", f"60 file sekaligus; batas rancangan 1 menit. Run kedua {r2.duration_s:.1f} detik.".replace(".", ",")),
    kp("sky", I(tot_in), "unit diproduksi (input)", f"Dari baris yang lolos validasi: OK {I(tot_ok)}, NG {I(tot_ng)}."),
    '</div><h3>1.1 Data simulasi (mentah dan bersih)</h3>')
rp1 += '<div class="card"><h4>Tabel 1.1. Satu baris yang sama di tiga versi template: isi mentah (staging) dan hasil bersih (production_log)</h4>' + table(
    ["File", "Baris di Excel", "Versi", "Isi mentah (<code>stg_raw_rows</code>)", "Hasil bersih"],
    [[f"<code>{r[0]}</code>", I(r[1]), r[2], f"<code>{esc(r[3])}</code>", f"{r[4]}, {r[5]}, {r[6]}, input {I(r[7])}, OK {I(r[8])}, NG {I(r[9])}"] for r in sample]) + \
    '<p>Contoh stasiun Reflow Soldering, model Pro, Shift 2, baris data ke-5 tiap file. Format tanggal dan cara menulis OK/NG berbeda per versi; setelah transform bentuknya seragam. Data dibuat dengan seed tetap, jadi cuplikan sama setiap dijalankan ulang.</p></div>'
rp1 += '<div class="card"><h4>Tabel 1.2. Tiga versi template log (inventaris dari semua file)</h4>' + table(
    ["Versi", "Bulan", "File", "Baris data", "Baris judul", "File dengan sel gabungan", "Baris kosong", "Baris TOTAL", "Header di baris"],
    [[k, {"v1": "Mar–Apr", "v2": "Mei–Jun", "v3": "Jul–Agu"}[k], I(r.files), I(r.data_rows), I(r.title_rows), I(r.merged_cells), I(r.blank_rows), I(r.summary_rows), I(r.header_row)] for k, r in tv.iterrows()]) + \
    '<p>Versi template ditentukan dari isi header, bukan dari nama file. Pemetaan kolom ada di <code>project/data/reference/column_mapping.yml</code>.</p></div>'
rp1 += '<h3>1.2 Tabel di database (<code>production.duckdb</code>)</h3><div class="card"><h4>Tabel 1.2a. Isi database</h4>' + table(
    ["Tabel", "Baris", "Isi"],
    [["stg_raw_rows", I(dbc["stg_raw_rows"]), "Satu baris data mentah apa adanya (JSON), lengkap dengan file, nomor baris, dan versi template."],
     ["production_log", I(dbc["production_log"]), "Hasil bersih satu stasiun, model, shift, hari. Kunci unik (date, station, model, shift) mencegah data ganda."],
     ["rejected_rows", I(dbc["rejected_rows"]), f"Pelanggaran aturan validasi (karantina): {I(n_rej_rows)} baris, sebagian melanggar lebih dari satu aturan."],
     ["etl_run_log", I(dbc["etl_run_log"]), "Satu baris per run: file dibaca, baris dibaca, valid, dimuat, ditolak, durasi."]]) + \
    f'<p>Jumlah baris production_log ({I(dbc["production_log"])}) ditambah baris karantina ({I(n_rej_rows)}) sama dengan baris data yang dibaca ({I(rows_read)}).</p></div>'
FILES = {"etl_runs": ("Riwayat run ETL (mentah)", "Q4, Q5"), "template_inventory": ("Inventaris versi template", "validasi"),
         "etl_runs_summary": ("Ringkasan run ETL dengan load dan reject rate", "Q4, Q5"), "issues_by_type": ("Jenis masalah dan perlakuannya", "Q1"),
         "dq_station": ("Data quality score per stasiun", "Q2"), "dq_file": ("Data quality score per file", "Q2"), "dq_month": ("Data quality score per bulan dan versi template", "Q3"),
         "dq_template": ("Data quality score per versi template", "Q3"), "prod_station_model_month": ("Output, yield, NG per stasiun, model, bulan", "Q7"),
         "prod_station": ("Output dan yield per stasiun", "Q7"), "prod_model": ("Output dan yield per model", "Q7"), "prod_month": ("Output dan yield per bulan", "Q7"),
         "ng_station_month": ("NG rate per stasiun dan bulan", "Q7, Q8"), "daily_trend": ("Tren harian dan rata-rata bergerak 7 hari", "Q8"), "daily_spikes": ("Hari-stasiun dengan lonjakan NG (z > 3)", "Q8"),
         "crosscheck": ("SQL vs pandas", "Q11"), "reconciliation": ("Rekonsiliasi per file: file = database + karantina", "Q11"), "reconciliation_excel": ("Rekonsiliasi dihitung ulang di Excel", "Q11"),
         "total_row_check": ("Baris TOTAL v3 vs jumlah baris data", "Q11"), "rerun_test": ("Uji run ulang, pemulihan, dan perbaikan karantina", "Q6, Q12"),
         "impact_steps": ("Menit per langkah penyusunan laporan", "Q9"), "impact": ("Skenario jam dihemat per tahun", "Q9"), "wait_time": ("Waktu tunggu laporan sebelum dan sesudah ETL", "Q10"),
         "issue_recovery": ("Masalah ditanam vs ditangani", "Q1, validasi"), "ground_truth_check": ("Lima fakta yang ditanam vs temuan", "validasi")}
resfiles = sorted(p for d in (RES_PREP, RES_ANALYSIS) for p in d.glob("*.csv"))
miss = [p.stem for p in resfiles if p.stem not in FILES]
assert not miss, f"CSV hasil belum didokumentasikan di FILES: {miss}"
rp1 += '<div class="card"><h4>Tabel 1.2b. Data hasil analisis (<code>project/results/</code>)</h4>' + table(
    ["File", "Isi", "Baris", "Menjawab"], [[f"<code>{p.stem}.csv</code>", FILES[p.stem][0], I(len(pd.read_csv(p))), FILES[p.stem][1]] for p in resfiles]) + \
    f'<p>{I(len(resfiles))} file CSV, ditambah {I(len(list(RES_PRESENT.glob("dash_*.csv"))))} CSV data dashboard dan <code>reconciliation.xlsx</code>.</p></div>'
rp1 += '<h3>1.3 Angka kunci (KPI)</h3><div class="card"><h4>Tabel 1.3. Lima KPI (definisi di <code>project/docs/definitions.md</code>)</h4>' + table(
    ["KPI", "Rumus ringkas", "Hasil", "Jumlah data"],
    [["Load rate", "baris dimuat ÷ baris data", P(r1.load_rate, 1), f"{I(r1.rows_inserted)} dari {I(rows_read)} baris"],
     ["Reject rate", "baris dikarantina ÷ baris data", P(r1.reject_rate, 1), f"{I(r1.rows_rejected)} baris"],
     ["Data quality score", "baris bersih ÷ baris data", f"{D(dq0.dq_score, 1)}%", f"{I(dq0.rows_clean)} dari {I(dq0.rows_total)} baris per stasiun"],
     ["Waktu proses", "durasi satu run ETL", f"{r1.duration_s:.1f} detik".replace(".", ","), f"{I(nfile)} file"],
     ["Jam dihemat (estimated)", "(menit manual − menit ETL) × laporan per tahun ÷ 60", f"{D(ip.jam_dihemat_per_tahun, 1)} jam per tahun", f"{I(ip.laporan_per_bulan)} laporan per bulan"]]) + \
    '<p>Baris bersih = dimuat tanpa perbaikan. Baris yang dimuat setelah perbaikan format otomatis dihitung terpisah (Tabel 2.1c).</p></div>'

# ---------------------------------------------------------------- 2. business questions
s21 = mk('<h3 id="sec21">2.1 Kualitas data mentah <span class="qlist">Q1, Q2, Q3</span></h3><div class="card">',
         Q(1, f"Masalah yang paling sering adalah OK + NG tidak sama dengan input (R04): {I(iss_q.loc['R04'].baris)} pelanggaran ({P(iss_q.loc['R04'].pct_baris, 1)} baris), sebagian karena angka negatif dan sebagian karena rumus tertimpa. "
              f"Kolom wajib kosong (R01), jumlah negatif (R03), dan baris ganda (R05) masing-masing {I(iss_q.loc['R01'].baris)} ({P(iss_q.loc['R01'].pct_baris, 1)}). Dua jenis lain tidak dikarantina tetapi diperbaiki formatnya: model tidak baku dan angka bersatuan teks, masing-masing {I(iss_f.iloc[0].baris)} baris. "
              f"Seluruhnya {I(n_issue)} masalah mengenai {P(n_issue / rows_read, 1)} baris; {I(r1.rows_rejected)} baris ({P(r1.reject_rate, 1)}) perlu karantina."),
         Q(2, f"Tidak ada yang menonjol: setiap stasiun punya data quality score {D(dq0.dq_score, 1)}% ({I(dq0.rows_rejected)} baris karantina dari {I(dq0.rows_total)}) dan setiap file {I(dqf.rows_rejected.iloc[0])} baris karantina dari {I(dqf.rows_total.iloc[0])}. "
              f"Generator menyebar masalah merata, jadi peringkat stasiun atau file tidak informatif. Di data nyata, tabel yang sama (Tabel 2.1c) akan menunjukkan stasiun dan file yang perlu dibenahi lebih dulu.", warn=True),
         Q(3, f"Tidak berubah. Reject rate {P(dqm.reject_rate.iloc[0], 1)} di keenam bulan dan di ketiga versi template ({', '.join(ver.index)}), karena generator memasang jumlah masalah yang sama tiap file. "
              f"Pertanyaan ini baru bisa dijawab bermakna dengan data nyata atau generator yang mengubah campuran masalah per bulan.", warn=True),
         '<h4>Grafik 2.1a. Pelanggaran aturan validasi (baris dikarantina)</h4>',
         hbars([(f"{r.kode}: {r.jenis}", r.baris, BLUE if r.kode == "R04" else GREY, f"{r.kode}: {r.jenis}, {I(r.baris)} pelanggaran ({P(r.pct_baris, 1)} baris)") for r in iss[iss.perlakuan == "Dikarantina"].itertuples()],
               lambda v: I(v), "Pelanggaran per aturan", 200),
         '<h4>Tabel 2.1b. Jenis masalah dan perlakuannya</h4>',
         table(["Kode", "Jenis masalah", "Perlakuan", "Baris", "% dari baris data"], [[f"<code>{r.kode}</code>", cs(r.jenis), r.perlakuan, I(r.baris), P(r.pct_baris, 1)] for r in iss.itertuples()]),
         f'<p>Baris dengan angka negatif melanggar R03 dan R04 sekaligus, jadi {I(nrule)} pelanggaran jatuh pada {I(r1.rows_rejected)} baris karantina.</p>',
         '<h4>Tabel 2.1c. Data quality score per stasiun</h4>',
         table(["Stasiun", "Baris data", "Bersih", "Diperbaiki otomatis", "Dikarantina", "DQ score", "Reject rate"],
               [[r.station, I(r.rows_total), I(r.rows_clean), I(r.rows_fixed), I(r.rows_rejected), f"{D(r.dq_score, 1)}%", P(r.reject_rate, 1)] for r in dqs.sort_values("ord").itertuples()]),
         '<h4>Tabel 2.1d. Data quality score per bulan</h4>',
         table(["Bulan", "Versi template", "Baris data", "Bersih", "Diperbaiki", "Dikarantina", "DQ score"],
               [[mlab(r.month), r.template_version, I(r.rows_total), I(r.rows_clean), I(r.rows_fixed), I(r.rows_rejected), f"{D(r.dq_score, 1)}%"] for r in dqm.itertuples()]), '</div>')
s22 = mk('<h3 id="sec22">2.2 Proses ETL <span class="qlist">Q4, Q5, Q6</span></h3><div class="card">',
         Q(4, f"{P(r1.load_rate, 1)} baris dimuat otomatis ({I(r1.rows_inserted)} dari {I(rows_read)}) dan {P(r1.reject_rate, 1)} ({I(r1.rows_rejected)}) masuk karantina. Dari baris yang dimuat, {I(n_fixfmt)} diperbaiki formatnya secara otomatis. Tidak ada baris yang hilang: dimuat + dikarantina = dibaca di kedua run."),
         Q(5, f"Satu run untuk {I(nfile)} file selesai dalam {D(r1.duration_s, 1)} detik (run pertama, memuat {I(r1.rows_inserted)} baris) dan {D(r2.duration_s, 1)} detik (run kedua, tidak ada baris baru), jauh di bawah batas 1 menit pada rancangan. Diukur di satu mesin; di mesin lain angkanya berbeda."),
         Q(6, f"Ya. Run kedua memuat {I(r2.rows_inserted)} baris baru, dan pada uji run ke-3 isi ketiga tabel (jumlah baris dan checksum) tidak berubah ({okc(rpt('A.'))} dari {len(rpt('A.'))} pemeriksaan PASS). "
              f"Jika {I(100)} baris production_log dihapus lalu ETL dijalankan lagi, tepat {I(100)} baris itu kembali dan isi tabel sama seperti semula ({okc(rpt('B.'))} dari {len(rpt('B.'))} PASS)."),
         '<h4>Tabel 2.2a. Riwayat run ETL</h4>',
         table(["Run", "File", "Baris dibaca", "Dilewati (kosong, TOTAL)", "Lolos validasi", "Baru dimuat", "Dikarantina", "Load rate", "Reject rate", "Durasi (detik)"],
               [[I(r.run_id), I(r.files_read), I(r.rows_read), I(r.rows_skipped), I(r.rows_valid), I(r.rows_inserted), I(r.rows_rejected), P(r.load_rate, 1), P(r.reject_rate, 1), D(r.duration_s, 1)] for r in runs.itertuples()]),
         '<p>Pada run kedua semua baris valid sudah ada, jadi kunci unik menolaknya secara diam-diam; baris karantina tidak bertambah karena sudah tercatat.</p>',
         '<h4>Tabel 2.2b. Uji run ulang dan pemulihan (salinan database)</h4>',
         table(["Uji", "Pemeriksaan", "PASS"], [["A. Run ke-3 pada file yang sama", "baris baru, isi staging, karantina, production_log, riwayat run", f"{okc(rpt('A.'))} dari {len(rpt('A.'))}"],
                                               ["B. 100 baris production_log dihapus", "jumlah turun, run ulang memulihkan tepat 100 baris, isi kembali sama", f"{okc(rpt('B.'))} dari {len(rpt('B.'))}"]]), '</div>')
trend_x = [TGL(d) for d in dtr.date]
s23 = mk('<h3 id="sec23">2.3 Query analitik <span class="qlist">Q7, Q8</span></h3><div class="card">',
         Q(7, f"Total {I(tot_in)} unit diproduksi pada {I(nfile)} file yang lolos validasi, yield {P(tot_ok / tot_in, 2)}. Per stasiun yield terendah {low.station} ({P(low['yield'], 1)}, NG {I(low.ng_qty)}) dan tertinggi {high.station} ({P(high['yield'], 1)}). "
              f"Per model: " + ", ".join(f"{r.model} {P(r['yield'], 2)}" for _, r in pmd.iterrows()) + ". Per bulan yield stabil di " + f"{P(pmo['yield'].min(), 2)} sampai {P(pmo['yield'].max(), 2)}. Angka lengkap per stasiun, model, dan bulan ada di <code>prod_station_model_month.csv</code> ({I(len(psm))} baris)."),
         Q(8, f"Tren harian datar: NG rate harian rata-rata {P(dtr.ng_rate.mean(), 2)} (kisaran {P(dtr.ng_rate.min(), 2)} sampai {P(dtr.ng_rate.max(), 2)}); rata-rata 7 hari bergerak di {P(dtr.ng_rate_ma7.min(), 2)} sampai {P(dtr.ng_rate_ma7.max(), 2)}. "
              f"Ada {I(len(dsp))} hari-stasiun dengan lonjakan (z > 3), terbesar {dsp.iloc[0].station} pada {TGL(dsp.iloc[0].date)} (NG rate {P(dsp.iloc[0].ng_rate, 2)}, z {D(dsp.iloc[0].z, 1)}). "
              f"Kenaikan NG di Reflow Soldering pada bulan ke-4 yang direncanakan tidak ada di data: Juni {P(rf.loc['2026-06'], 2)} berada di kisaran bulan lain ({P(rf_other.min(), 2)} sampai {P(rf_other.max(), 2)}). Lonjakan hari-stasiun di atas belum tentu bermakna: dengan banyak hari-stasiun yang diperiksa, beberapa lonjakan muncul karena kebetulan."),
         '<h4>Grafik 2.3a. NG rate per stasiun (seluruh bulan)</h4>',
         hbars([(r.station, r.ng_qty / r.input_qty, BLUE if r.station == "Reflow Soldering" else GREY, f"{r.station}: NG {I(r.ng_qty)} dari {I(r.input_qty)} unit, yield {P(r._6, 2)}") for r in pst.itertuples()],
               lambda v: P(v, 1), "NG rate per stasiun", 0.05),
         '<h4>Tabel 2.3b. Output, yield, dan NG per stasiun</h4>',
         table(["Stasiun", "Input", "OK", "NG", "Yield"], [[r.station, I(r.input_qty), I(r.ok_qty), I(r.ng_qty), P(r._6, 2)] for r in pst.itertuples()]),
         '<h4>Tabel 2.3c. Output, yield, dan NG per model dan per bulan</h4>',
         table(["Kelompok", "Input", "OK", "NG", "Yield"], [[f"Model {r.model}", I(r.input_qty), I(r.ok_qty), I(r.ng_qty), P(r._5, 2)] for r in pmd.itertuples()] +
               [[mlab(r.month), I(r.input_qty), I(r.ok_qty), I(r.ng_qty), P(r._5, 2)] for r in pmo.itertuples()]),
         '<h4>Tabel 2.3d. NG rate per stasiun dan bulan</h4>',
         table(["Stasiun"] + [mlab(m) for m in tbl.columns], [[k] + [P(v, 2) for v in row] for k, row in tbl.iterrows()]),
         '<h4>Grafik 2.3e. NG rate harian dan rata-rata bergerak 7 hari (semua stasiun)</h4>',
         lines(trend_x, [("Rata-rata 7 hari", BLUE, 2.5, list(dtr.ng_rate_ma7)), ("NG rate harian", GREY, 1.2, list(dtr.ng_rate))], lambda v: P(v, 1), "NG rate harian", zero=True),
         legend([(GREY, "NG rate harian"), (BLUE, "Rata-rata bergerak 7 hari")]),
         '<h4>Tabel 2.3f. Hari-stasiun dengan lonjakan NG (z-score terhadap rata-rata stasiun, z > 3)</h4>',
         table(["Stasiun", "Tanggal", "Input", "NG", "NG rate", "Rata-rata stasiun", "z"], [[r.station, TGL(r.date), I(r.input_qty), I(r.ng_qty), P(r.ng_rate, 2), P(r.mean_ng_rate, 2), D(r.z, 1)] for r in dsp.itertuples()]),
         '<p>Query ada di <code>project/code/2-analysis/sql/03_views.sql</code>; semua angka dicek silang dengan pandas (Tabel 2.5d).</p></div>')
steps_c = ist.rename(columns={"langkah": "l"})
s24 = mk('<h3 id="sec24">2.4 Dampak <span class="qlist">Q9, Q10</span></h3><div class="card">',
         Q(9, f"Sekitar {D(ip.jam_dihemat_per_tahun, 1)} jam per tahun pada {I(ip.laporan_per_bulan)} laporan per bulan: satu laporan turun dari {D(ip.menit_manual, 0)} menit menjadi {D(ip.menit_etl, 1)} menit. Dengan {I(4)} laporan per bulan hasilnya {D(isc.loc[4].jam_dihemat_per_tahun, 1)} jam, dengan {I(12)} laporan {D(isc.loc[12].jam_dihemat_per_tahun, 1)} jam. "
              f"Menit per langkah sebelum ETL adalah asumsi penyusun, bukan hasil stopwatch; hanya durasi run ETL yang terukur. Angka berlabel estimated.", warn=True),
         Q(10, f"Waktu dari data tersedia sampai laporan siap turun dari {D(wt.jam.iloc[0], 0)} jam (asumsi manual) menjadi sekitar {D(wt.jam.iloc[1] * 60, 0)} menit ({D(wt.jam.iloc[1], 2)} jam), pengurangan {P(wt.pengurangan.iloc[1], 0)}. Angka setelah ETL adalah asumsi waktu tinjau karantina ditambah durasi run yang terukur; angka sebelum ETL asumsi penuh.", warn=True),
         '<h4>Grafik 2.4a. Menit per langkah penyusunan laporan: manual vs setelah ETL (asumsi)</h4>',
         gbars(list(ist.langkah), [("Manual", GREY, list(ist.menit_manual)), ("Setelah ETL", BLUE, list(ist.menit_setelah_etl))], lambda v: I(v), "Menit per langkah", rot=0),
         legend([(GREY, "Manual"), (BLUE, "Setelah ETL")]),
         '<h4>Tabel 2.4b. Menit per langkah (estimated, simulated)</h4>',
         table(["Langkah", "Menit manual", "Menit setelah ETL", "Menit dihemat"], [[r.langkah, I(r.menit_manual), I(r.menit_setelah_etl), I(r.menit_dihemat)] for r in ist.itertuples()] +
               [["<b>Total</b>", I(ist.menit_manual.sum()), I(ist.menit_setelah_etl.sum()), I(ist.menit_dihemat.sum())]]),
         '<h4>Tabel 2.4c. Jam dihemat per tahun menurut jumlah laporan per bulan</h4>',
         table(["Laporan per bulan", "Laporan per tahun", "Menit manual", "Menit setelah ETL (termasuk durasi run)", "Jam dihemat per tahun", "Dipakai"],
               [[I(r.laporan_per_bulan), I(r.laporan_per_tahun), D(r.menit_manual, 0), D(r.menit_etl, 2), D(r.jam_dihemat_per_tahun, 1), "Ya" if r.dipakai == "ya" else "Skenario"] for r in imp.itertuples()]),
         '<h4>Tabel 2.4d. Waktu tunggu laporan (jam)</h4>',
         table(["Kondisi", "Jam", "Pengurangan"], [[r.kondisi, D(r.jam, 2), P(r.pengurangan, 0)] for r in wt.itertuples()]),
         '<p>Jam dihemat = (menit manual − menit ETL) × laporan per tahun ÷ 60. Dampak dihitung dalam jam kerja, belum dalam rupiah.</p></div>')
tr_min, tr_max, tr_mean = tr.selisih.min(), tr.selisih.max(), tr.selisih.mean()
gm = [("A. Run ke-3: tidak ada perubahan", "A."), ("B. Data dihapus lalu dipulihkan", "B."), ("C. Perbaikan karantina dan muat ulang", "C.")]
s25 = mk('<h3 id="sec25">2.5 Validitas dan otomatisasi <span class="qlist">Q11, Q12, Q13</span></h3><div class="card">',
         Q(11, f"Ya, pada seluruh {I(len(rc))} file: baris, input, OK, dan NG di file = database + karantina (selisih 0). Total di file {I(rec_tot.input_file)} unit = database {I(rec_tot.input_db)} + karantina {I(rec_tot.input_quarantine)}. "
               f"Dihitung dengan SQL, pandas ({okc(cx)} dari {len(cx)} cek silang PASS), dan rumus Excel ({okc(rx)} dari {len(rx)} PASS). "
               f"Catatan: baris TOTAL di {I(len(tr))} file v3 berbeda {I(tr_min)} sampai {I(tr_max)} unit (rata-rata {I(tr_mean)}) dari jumlah baris data di file yang sama, jadi baris TOTAL tidak dipakai sebagai pembanding."),
         Q(12, f"Ya. Dari {I(rr.iloc[8].expected)} baris karantina yang bisa diperbaiki, semuanya dimuat ulang setelah diperbaiki; {I(5)} perbaikan yang salah (OK + NG tidak sama dengan input) ditolak lagi dan tidak masuk. "
               f"Isi {I(r1.rows_inserted)} baris yang sudah ada tidak berubah (checksum sama), dan hasil akhir {I(7200)} baris sama dengan data bersih asal. Salinan baris ganda ({I(60)}) memang dibuang, bukan diperbaiki ({okc(rpt('C.'))} dari {len(rpt('C.'))} pemeriksaan PASS)."),
         Q(13, "Sebagian. Dua workflow GitHub Actions ditulis: <code>ci.yml</code> menjalankan test setiap push dan <code>daily_etl.yml</code> menjalankan ETL terjadwal setiap hari. Keduanya belum terbukti jalan di GitHub sampai branch di-push dan dijalankan; "
                "pada simulasi ini jadwal harian membuat ulang file log dengan generator, bukan menunggu file operator yang sesungguhnya masuk.", warn=True),
         '<h4>Tabel 2.5a. Rekonsiliasi total: file asli = database + karantina</h4>',
         table(["Ukuran", "Di file Excel", "Di database", "Di karantina", "Selisih"],
               [[lab, I(rec_tot[f"{k}_file"]), I(rec_tot[f"{k}_db"]), I(rec_tot[f"{k}_quarantine"]), I(rec_tot[f"{k}_file"] - rec_tot[f"{k}_db"] - rec_tot[f"{k}_quarantine"])] for lab, k in
                (("Baris data", "rows"), ("Input", "input"), ("OK", "ok"), ("NG", "ng"))]),
         f'<p>Rekonsiliasi per file: {okc(rc)} dari {len(rc)} PASS (<code>reconciliation.csv</code>); dihitung ulang dengan rumus Excel di <code>reconciliation.xlsx</code>: {okc(rx)} dari {len(rx)} PASS.</p>',
         '<h4>Tabel 2.5b. Masalah ditanam vs ditangani</h4>',
         table(["Jenis masalah", "Ditanam", "Ditangani benar", "Tindakan yang diharapkan"], [[r.jenis_masalah, I(r.ditanam), I(r.ditangani_benar), r.tindakan_diharapkan] for r in rec.itertuples()]),
         '<h4>Tabel 2.5c. Uji perbaikan karantina dan muat ulang</h4>',
         table(["Kelompok uji", "Pemeriksaan", "PASS"], [[lab, I(len(rpt(p))), I(okc(rpt(p)))] for lab, p in gm]),
         '<h4>Tabel 2.5d. Cek silang SQL vs pandas</h4>',
         table(["Pemeriksaan", "Jumlah dibandingkan", "Selisih terbesar", "Hasil"], [[cs(r.check), I(r.n_compared), ("0" if r.max_abs_diff == 0 else "&lt; 0,000001"), OK("PASS") if r.status == "PASS" else NO("FAIL")] for r in cx.itertuples()]),
         '<h4>Tabel 2.5e. Workflow otomatis</h4>',
         table(["File", "Pemicu", "Isi", "Status"],
               [["<code>.github/workflows/ci.yml</code>", "setiap push dan pull request", "pytest, lalu smoke test pipeline penuh (generate, ETL, query)", PART("Ditulis, belum dijalankan di GitHub")],
                ["<code>.github/workflows/daily_etl.yml</code>", "jadwal harian dan manual", "generate, ETL, simpan hasil sebagai artifact", PART("Ditulis, belum dijalankan di GitHub")]]), '</div>')
SEC = {1: "21", 2: "21", 3: "21", 4: "22", 5: "22", 6: "22", 7: "23", 8: "23", 9: "24", 10: "24", 11: "25", 12: "25", 13: "25"}
rp2_body = mk(s21, s22, s23, s24, s25)
qn_uniq = sorted(set(int(x) for x in re.findall(r'<span class="qn">Q(\d+)</span>', rp2_body)))
assert qn_uniq == list(range(1, 14)), qn_uniq
nw = len(WARN)
wtxt = ", ".join(f"Q{n}" for n in sorted(WARN))
chips = mk('<div class="qchips">', "".join(f'<a class="qc{" w" if n in WARN else ""}" href="#sec{SEC[n]}" title="{esc(QT[n])}">Q{n}</a>' for n in range(1, 14)), '</div>')
rp2 = mk(f'<div class="card"><p><b>Jawaban singkat:</b> semua {len(QT)} pertanyaan terjawab ({npr["Utama"]} Utama, {npr["Pendukung"]} Pendukung, {npr["Tambahan"]} Tambahan). '
         f'{nw} jawaban dengan catatan (kuning): {wtxt}. Klik nomor pertanyaan untuk melompat ke pembahasannya. Pertanyaan utama project dijawab di bagian 7.</p>',
         chips, '<p class="report-note">Q hijau = terjawab, Q kuning = terjawab dengan catatan. Pembahasan dikelompokkan per tema (2.1 sampai 2.5).</p></div>', rp2_body)

# ---------------------------------------------------------------- 3-5. dataset, tools, alur
npy = len(list((REPO / "project/code").rglob("*.py")))
loc = sum(len(p.read_text(encoding="utf-8").splitlines()) for p in (REPO / "project/code").rglob("*.py"))
nsql = len(list((REPO / "project/code").rglob("*.sql")))
ntest = len(list((REPO / "project/tests").glob("test_*.py")))
fm = lambda r: OK("Ditemukan") if r == "Sesuai" else PART(r)
rp3 = mk('<div class="card"><p><b>Jawaban singkat:</b> ukuran dataset sesuai rancangan dan dibuat ulang dengan seed tetap. Dari lima fakta yang ditanam, hanya satu (merged cell, subtotal, baris kosong) terwujud penuh; empat lainnya sebagian: '
         'tidak ada template khusus AOI Inspection, tidak ada tanggal serial Excel, variasi model lebih sempit, dan masalah tidak valid lebih banyak dari 2–3% sementara kenaikan NG Reflow bulan ke-4 tidak ada. Tidak ada masalah lisensi karena data buatan sendiri.</p></div>',
         table(["Aspek", "Rancangan", "Realisasi", "Verdict"], [
             ["Sumber", "Simulasi buatan sendiri, skrip generate_messy_logs.py", "Skrip <code>01_generate_messy_logs.py</code>, seed 33260302, hasil identik setiap dijalankan (sidik jari SHA-256 sama pada dua kali jalan)", OK("Sesuai")],
             ["Ukuran", "10 stasiun, 3 model, 2 shift, ±6 bulan, ±60 file", f"{I(nsta)} stasiun, 3 model, 2 shift, {I(len(dqm))} bulan, {I(nfile)} file", OK("Sesuai")],
             ["Jumlah baris", "±7.000 baris produksi", f"{I(rows_read)} baris data (7.200 baris bersih ditambah {I(60)} salinan ganda yang ditanam)", OK("Sesuai")],
             ["Tabel", "stg_raw_rows, production_log, rejected_rows, etl_run_log", "Keempatnya. Kolom etl_run_log: rows_read, rows_skipped, rows_valid, rows_inserted, rows_rejected (rancangan: rows_loaded)", PART("Sesuai + penyesuaian")],
             ["Fakta 1: tiga versi template, termasuk satu khusus AOI Inspection", "Tiga versi, satu khusus AOI", cs(gtm.loc[1].ditemukan), fm(gtm.loc[1].hasil)],
             ["Fakta 2: format tanggal campuran termasuk angka serial Excel", "Campuran, termasuk serial", cs(gtm.loc[2].ditemukan), fm(gtm.loc[2].hasil)],
             ["Fakta 3: nama model beragam (Pro, PRO, pro, Model Pro)", "Beragam", cs(gtm.loc[3].ditemukan), fm(gtm.loc[3].hasil)],
             ["Fakta 4: merged cell, subtotal, baris kosong", "Dilewati tanpa kehilangan data", cs(gtm.loc[4].ditemukan), fm(gtm.loc[4].hasil)],
             ["Fakta 5: 2–3% nilai tidak valid; NG Reflow naik di bulan ke-4", "2–3% tidak valid, kenaikan Reflow", cs(gtm.loc[5].ditemukan), fm(gtm.loc[5].hasil)],
             ["Lisensi", "Tidak memakai data perusahaan", "Tidak ada dataset pihak ketiga, tidak perlu dicek", OK("Tidak berlaku")]]))
rp4 = mk('<div class="card"><p><b>Jawaban singkat:</b> tools inti dipakai sesuai rancangan. Pandera tidak dipakai (opsional, aturan ditulis sebagai fungsi Python); dashboard dibuat dan diuji lokal tetapi belum di-deploy; '
         'GitHub Actions ditulis tetapi belum terbukti jalan; Excel dihitung ulang oleh LibreOffice.</p></div>',
         table(["Tool", "Rancangan", "Realisasi", "Verdict"], [
             ["Python (pandas, openpyxl)", "openpyxl membaca Excel, pandas merapikan, satu perintah", f"openpyxl membaca semua template; transform ditulis sebagai fungsi Python biasa; pandas dipakai untuk cek silang dan analisis ({I(npy)} skrip dan modul, {I(loc)} baris). Perintah: <code>02_run_etl.py</code>", PART("Sesuai + penyesuaian")],
             ["DuckDB + SQL", "Database tujuan, kunci unik, query dan rekonsiliasi", f"production.duckdb dengan kunci unik dan constraint; {I(nsql)} file SQL (skema dan view)", OK("Sesuai")],
             ["Pandera (opsional)", "Aturan validasi sebagai schema", "Tidak dipakai; aturan R01–R05 ditulis sebagai fungsi Python (sesuai cadangan pada rancangan) dan diuji satu per satu", OK("Sesuai")],
             ["pytest + GitHub Actions", "Unit test tiap aturan, uji run ulang, rekonsiliasi; berjalan otomatis", f"{ntest} file test, 37 test lulus secara lokal; <code>ci.yml</code> ditulis tetapi belum dijalankan di GitHub", PART("Sebagian")],
             ["Streamlit + Plotly", "Dashboard 3 halaman, bisa dibuka lewat link", "<code>streamlit/app.py</code> 3 halaman (ringkasan produksi, kualitas data dan karantina, dampak waktu); diuji dengan <code>AppTest</code>; belum di-deploy", PART("Sebagian")],
             ["Excel + GitHub", "Cek silang total dengan file asli; kode di GitHub", f"<code>reconciliation.xlsx</code> dengan rumus yang dihitung ulang oleh LibreOffice ({I(len(rx))} pemeriksaan), bukan Microsoft Excel; kode di branch <code>project-33-build</code>, belum digabung ke <code>main</code>", PART("Sesuai + penyesuaian")],
             ["Jupyter", "Notebook kualitas data", "<code>analysis.ipynb</code> dibuat otomatis dan dieksekusi tanpa error", PART("Sesuai + tambahan")],
             ["PyYAML", "Tidak disebut", "Membaca <code>column_mapping.yml</code> sehingga template baru cukup menambah konfigurasi", PART("Tambahan")]]))
steps = [("1", "Menginventaris file dan format", "<code>template_inventory.md</code>, <code>template_inventory.csv</code>", OK("Sesuai"), ""),
         ("2", "Merancang skema target dan aturan", "<code>data_dictionary.md</code>, <code>validation_rules.md</code>, <code>column_mapping.yml</code>", OK("Sesuai"), ""),
         ("3", "Membuat generator log berantakan", "<code>01_generate_messy_logs.py</code>", PART("Sebagian"), "Template AOI khusus, tanggal serial, dan kenaikan Reflow bulan ke-4 tidak dibuat; masalah tidak valid 4,1% baris karantina (rancangan 2–3%)."),
         ("4", "Membangun extract dan transform", "<code>etl/extract.py</code>, <code>etl/transform.py</code>", OK("Sesuai"), "Template baru cukup ditambah di file konfigurasi."),
         ("5", "Membangun validasi dan load", "<code>etl/validate_load.py</code>, <code>01_schema.sql</code>, <code>02_run_etl.py</code>", OK("Sesuai"), ""),
         ("6", "Menulis test dan rekonsiliasi", "<code>tests/</code>, <code>05_reconcile.py</code>, <code>06_rerun_and_reload.py</code>", PART("Sesuai + tambahan"), "Ditambah cek silang pandas dan rekonsiliasi per file; belum dijalankan di GitHub Actions."),
         ("7", "Membuat profil kualitas data", "<code>03_run_queries.py</code>, notebook", OK("Sesuai"), "Hasil seragam antar stasiun, file, dan bulan."),
         ("8", "Menulis query analitik", "<code>03_views.sql</code>, <code>03_run_queries.py</code>", OK("Sesuai"), ""),
         ("9", "Menghitung dampak", "<code>07_impact.py</code>", OK("Sesuai"), "Menit manual adalah asumsi; berlabel estimated."),
         ("10", "Mencocokkan dengan fakta yang ditanam", "<code>08_ground_truth_check.py</code>", OK("Sesuai"), "Satu fakta penuh, empat sebagian (bagian 3)."),
         ("11", "Membuat laporan otomatis", "<code>streamlit/app.py</code>, <code>09_build_dashboard_data.py</code>", PART("Sebagian"), "Belum di-deploy; halaman Karantina digabung dengan Kualitas Data."),
         ("12", "Menulis README dan menyiapkan jadwal", "<code>README.md</code>, <code>daily_etl.yml</code>", PART("Sebagian"), "Workflow jadwal ditulis, belum dijalankan; branch menunggu review.")]
pyfiles = {p.name for p in (REPO / "project/code").rglob("*.py")}
need = {"01_generate_messy_logs.py", "02_run_etl.py", "03_run_queries.py", "05_reconcile.py", "06_rerun_and_reload.py", "07_impact.py", "08_ground_truth_check.py", "09_build_dashboard_data.py",
        "10_build_notebook.py", "11_build_readme.py", "extract.py", "transform.py", "validate_load.py", "common.py", "app.py"}
assert need <= pyfiles, need - pyfiles
for rel in ("project/docs/template_inventory.md", "project/docs/data_dictionary.md", "project/docs/validation_rules.md", "project/data/reference/column_mapping.yml", ".github/workflows/ci.yml", ".github/workflows/daily_etl.yml"):
    assert (REPO / rel).exists(), rel
rp5 = mk('<div class="card"><p><b>Jawaban singkat:</b> 12 langkah dijalankan sesuai urutan. Langkah 3 hanya sebagian terwujud (generator tidak membuat semua pola yang direncanakan), langkah 11 dan 12 belum selesai penuh (dashboard belum di-deploy, workflow belum dijalankan di GitHub), '
         'dan beberapa langkah ditambah (cek silang pandas, rekonsiliasi per file, uji pemulihan).</p></div>',
         table(["Langkah", "Rancangan", "Realisasi", "Verdict", "Catatan"], [[a, b, c, d, e] for a, b, c, d, e in steps]),
         '<div class="card"><h4>Penyesuaian dan improvisasi yang tidak ada di rancangan</h4><ul class="tight">',
         f'<li>Setiap masalah yang ditanam dicatat jenisnya, sehingga ketepatan penanganan bisa dihitung per jenis ({I(n_issue)} masalah, semuanya ditangani sesuai harapan) dan {I(cleanrow.ditanam)} baris tanpa masalah dipastikan dimuat tanpa berubah (tidak ada positif palsu).</li>',
         '<li>Ground truth hanya dibaca oleh skrip validasi, tidak oleh ETL, supaya pipeline tidak "mengintip" jawaban.</li>',
         f'<li>Uji pemulihan: {I(100)} baris dihapus lalu dipulihkan, dan perbaikan karantina yang salah ditolak ({okc(rr)} pemeriksaan semuanya PASS, dijalankan pada salinan database).</li>',
         f'<li>Rekonsiliasi dilakukan per file ({I(len(rc))} file) dan dihitung ulang dengan rumus Excel yang dihitung LibreOffice ({I(len(rx))} pemeriksaan), bukan angka yang ditulis tangan.</li>',
         '<li>Pemetaan kolom dan daftar stasiun dipindah ke <code>column_mapping.yml</code> supaya versi template baru tidak perlu mengubah kode.</li>',
         '<li>Notebook, README, dan halaman ini dibuat otomatis dari CSV hasil; angka halaman ini diaudit terhadap file hasil.</li></ul></div>')

# ---------------------------------------------------------------- 6. output
chk = lambda rel: (REPO / rel).exists()
outs = [("Pipeline ETL", "Utama", OK("Tercapai"), "Paket <code>etl/</code> dan perintah <code>02_run_etl.py</code>; satu perintah membaca, merapikan, memvalidasi, dan memuat; aman dijalankan ulang"),
        ("Laporan produksi otomatis", "Utama", PART("Sebagian"), "<code>streamlit/app.py</code> (3 halaman) diuji lokal dengan AppTest; link publik belum ada"),
        ("Database & query SQL", "Utama", OK("Tercapai"), f"<code>production.duckdb</code> (dibuat ulang, tidak di-commit) dengan 4 tabel dan {I(nsql)} file SQL"),
        ("Laporan kualitas data", "Utama", OK("Tercapai"), "<code>analysis.ipynb</code> dan CSV di <code>project/results/2-analysis/</code>"),
        ("Generator log berantakan", "Utama", OK("Tercapai"), "<code>01_generate_messy_logs.py</code>, seed tetap, hasil identik"),
        ("Test suite & rekonsiliasi", "Utama", PART("Sebagian"), f"{ntest} file test (37 test lulus lokal), <code>reconciliation.xlsx</code>; belum dijalankan otomatis di GitHub Actions"),
        ("Laporan temuan & rekomendasi", "Utama", OK("Tercapai"), "<code>README.md</code> dan halaman ini"),
        ("Jadwal ETL harian", "Opsional", PART("Sebagian"), "<code>daily_etl.yml</code> ditulis; belum dijalankan di GitHub")]
nU = [o for o in outs if o[1] == "Utama"]
cnt = lambda s: sum(1 for o in nU if s in o[2])
DOCS = [("docs/template_inventory.md", "Versi template dan masalah format", "project/docs/template_inventory.md"), ("docs/data_dictionary.md", "Kamus data 4 tabel", "project/docs/data_dictionary.md"),
        ("config/column_mapping.yml", "Pemetaan kolom per template", "project/data/reference/column_mapping.yml"), ("docs/validation_rules.md", "Aturan transform dan validasi", "project/docs/validation_rules.md"),
        ("scripts/generate_messy_logs.py", "Generator log", "project/code/1-data-preparation/python/01_generate_messy_logs.py"), ("data/raw_excel/", "File Excel simulasi (tidak di-commit)", "project/data/raw/logs"),
        ("data/ground_truth.json", "Pola yang ditanam (tidak di-commit)", "project/data/raw/ground_truth.json"), ("etl/extract.py", "Membaca file dan mengenali template", "project/code/1-data-preparation/python/etl/extract.py"),
        ("etl/transform.py", "Menyeragamkan data", "project/code/1-data-preparation/python/etl/transform.py"), ("etl/validate_load.py", "Validasi, karantina, load", "project/code/1-data-preparation/python/etl/validate_load.py"),
        ("production.duckdb", "File database (tidak di-commit)", "project/production.duckdb"), ("tests/", "Unit test", "project/tests"), (".github/workflows/ci.yml", "Test otomatis", ".github/workflows/ci.yml"),
        ("outputs/reconciliation.xlsx", "Rekonsiliasi Excel", "project/results/2-analysis/reconciliation.xlsx"), ("sql/", "Query dan view", "project/code/2-analysis/sql/03_views.sql"),
        ("notebooks/data_quality.ipynb", "Notebook kualitas data", "project/results/3-presentation/analysis.ipynb"), ("dashboard/app.py", "Dashboard Streamlit", "project/code/3-presentation/streamlit/app.py"),
        ("requirements.txt", "Paket Python", "project/requirements.txt"), ("README.md", "Laporan temuan", "README.md"), ("index.html", "Pengalihan ke design-and-report/", "index.html"),
        (".github/workflows/daily_etl.yml", "Jadwal ETL harian", ".github/workflows/daily_etl.yml")]
NOCOMMIT = ("production.duckdb", "project/data/raw")
stat_doc = lambda rel: PART("Tidak di-commit") if rel in NOCOMMIT or rel.startswith("project/data/raw") else (OK("Ada") if chk(rel) else NO("Belum ada"))
for a, b, c in DOCS:
    assert chk(c) or c in NOCOMMIT or c.startswith("project/data/raw") or c.endswith(".ipynb") or c.endswith(".xlsx"), c
rp6 = mk(f'<div class="card"><p><b>Jawaban singkat:</b> {I(cnt("Tercapai"))} dari {I(len(nU))} output Utama tercapai penuh dan {I(cnt("Sebagian"))} sebagian (laporan produksi belum punya link publik; test belum dijalankan di GitHub Actions). '
         f'Jadwal ETL harian (Opsional) ditulis tetapi belum dijalankan.</p></div>',
         table(["Output", "Label", "Status", "Bukti"], [[f"<b>{a}</b>", b, c, d] for a, b, c, d in outs]),
         '<div class="card"><h4>Daftar dokumen pada rancangan vs repositori</h4>',
         table(["Dokumen (rancangan)", "Isi", "Lokasi sekarang", "Status"], [[f"<code>{a}</code>", b, f"<code>{c}</code>", stat_doc(c)] for a, b, c in DOCS]),
         '<p>File Excel simulasi, ground truth, dan <code>production.duckdb</code> tidak di-commit karena bisa dibuat ulang oleh skrip. Hasil <code>reconciliation.xlsx</code> dan notebook dibuat oleh skrip analisis dan presentasi.</p></div>')

# ---------------------------------------------------------------- 7. kesimpulan
crit = [("1. Kedelapan pertanyaan Utama terjawab dengan angka", OK("Tercapai"), "Q1, Q2, Q4, Q5, Q6, Q7, Q9, Q11 terjawab (bagian 2); Q2 dan Q9 dengan catatan"),
        ("2. Rekonsiliasi cocok: input, OK, NG di database + karantina = file asli", OK("Tercapai"), f"{okc(rc)} dari {len(rc)} file PASS; {okc(rx)} dari {len(rx)} pemeriksaan Excel PASS"),
        ("3. Menjalankan ETL dua kali menghasilkan jumlah baris sama, tanpa data ganda", OK("Tercapai"), f"Run kedua memuat {I(r2.rows_inserted)} baris baru; {okc(rr)} dari {len(rr)} uji PASS"),
        ("4. Semua pola ditanam tertangani atau terdeteksi, semua test lulus di GitHub Actions", PART("Sebagian"), f"{I(n_issue)} dari {I(n_issue)} masalah ditangani; 37 test lulus lokal; Actions belum dijalankan; empat fakta hanya sebagian ditanam"),
        ("5. Run ±60 file &lt; 1 menit; orang awam membaca laporan produksi &lt; 1 menit", PART("Sebagian"), f"Run {D(r1.duration_s, 1)} detik tercapai; keterbacaan oleh orang awam belum diuji"),
        ("6. Checklist standar (pertanyaan bisnis, cleaning, SQL, dashboard ter-deploy, README)", PART("Sebagian"), "Semua ada kecuali dashboard ter-deploy")]
ncr = sum(1 for c in crit if ">Tercapai<" in c[1])
rp7 = mk(
    '<div class="card"><h4>7.1 Hasil analisis: jawaban atas pertanyaan utama</h4>',
    '<p><i>Bagaimana mengubah log operator yang berantakan menjadi data siap analisis?</i></p><ul class="tight">',
    f'<li><b>Bisa dengan ETL yang aman dijalankan ulang:</b> {I(nfile)} file dalam 3 versi template dibaca, {I(r1.rows_inserted)} dari {I(rows_read)} baris ({P(r1.load_rate, 1)}) dimuat dalam {D(r1.duration_s, 1)} detik, dan run kedua tidak menggandakan data.</li>',
    f'<li><b>Tidak ada baris hilang atau diperbaiki diam-diam:</b> {I(r1.rows_rejected)} baris ({P(r1.reject_rate, 1)}) dikarantina beserta aturan yang gagal; rekonsiliasi {okc(rc)} dari {len(rc)} file cocok; perbaikan karantina bisa dimuat ulang tanpa merusak data lain.</li>',
    f'<li><b>Masalah terbanyak:</b> OK + NG tidak sama dengan input ({I(iss_q.loc["R04"].baris)} pelanggaran). Seluruh {I(n_issue)} masalah yang ditanam ditangani sesuai harapan.</li>',
    f'<li><b>Data bersih siap dianalisis:</b> yield total {P(tot_ok / tot_in, 2)}; Reflow Soldering paling rendah ({P(low["yield"], 1)}), Packaging paling tinggi ({P(high["yield"], 1)}).</li></ul></div>',
    '<div class="card"><h4>7.2 Impact</h4><ul class="tight">',
    f'<li><b>Nilai praktis (estimated, simulated):</b> waktu satu laporan turun dari {D(ip.menit_manual, 0)} menit menjadi {D(ip.menit_etl, 1)} menit; pada {I(ip.laporan_per_bulan)} laporan per bulan sekitar {D(ip.jam_dihemat_per_tahun, 1)} jam per tahun. Waktu tunggu laporan turun dari {D(wt.jam.iloc[0], 0)} jam menjadi sekitar {D(wt.jam.iloc[1] * 60, 0)} menit.</li>',
    '<li><b>Nilai analitis:</b> setiap angka di laporan bisa ditelusuri ke file dan baris asal lewat staging, dan angka itu sama dengan total file Excel asli.</li>',
    '<li><b>Nilai portofolio:</b> pipeline data engineering dasar yang lengkap: template berubah-ubah, validasi, karantina, load idempotent, rekonsiliasi, test, dan dashboard.</li>',
    '<li><b>Belum terukur:</b> waktu manual sebenarnya di lapangan dan ragam masalah log nyata. Semua angka berasal dari data simulasi dan menguji metode.</li></ul></div>')
rp7 += ('<div class="card"><h4>7.3 Success criteria</h4>' + table(["Kriteria (Design Project, bagian 8)", "Status", "Bukti"], [[a, b, c] for a, b, c in crit])
        + f'<p><b>Hasil:</b> {I(ncr)} dari {I(len(crit))} kriteria tercapai, {I(len(crit) - ncr)} sebagian.</p></div>')
rp7 += mk('<div class="card"><h4>7.4 Rekomendasi</h4><ul class="tight">',
          '<li>Jadikan ETL ini jalur standar masuknya log Excel, dan tinjau karantina secara berkala; jangan memperbaiki baris bermasalah secara otomatis.</li>',
          f'<li>Perbaiki template di sumbernya: masalah terbanyak adalah OK + NG tidak sama dengan input ({I(iss_q.loc["R04"].baris)} pelanggaran). Kolom NG sebagai rumus terkunci atau validasi input mencegahnya sejak awal (lihat Project 30).</li>',
          '<li>Pakai daftar pilihan untuk kolom model dan shift, dan pisahkan kolom OK dan NG, supaya perbaikan format otomatis tidak diperlukan.</li>',
          '<li>Tambahkan versi template baru lewat <code>column_mapping.yml</code>, tanpa mengubah kode ETL.</li></ul></div>')
rp7 += mk('<div class="card"><h4>7.5 Saran perbaikan</h4><ul class="tight">',
          '<li>Ukur menit per langkah penyusunan laporan dengan stopwatch pada beberapa laporan nyata, lalu ganti asumsi pada Tabel 2.4b.</li>',
          '<li>Perluas generator: template khusus AOI Inspection, tanggal serial Excel, variasi penulisan model yang lebih luas, campuran masalah yang berbeda per bulan dan stasiun, serta kenaikan NG Reflow bulan ke-4. Dengan itu Q2 dan Q3 baru bisa dijawab bermakna.</li>',
          '<li>Push branch, jalankan <code>ci.yml</code> dan <code>daily_etl.yml</code> di GitHub, lalu deploy dashboard dan uji keterbacaannya ke satu pembaca awam.</li>',
          '<li>Uji ETL pada beberapa log Excel nyata (dianonimkan) untuk melihat masalah yang tidak ada di simulasi.</li></ul></div>')
rp7 += mk('<div class="card"><h4>7.6 Batasan</h4><ul class="tight">',
          '<li>Semua temuan berasal dari data simulasi yang dibuat sendiri; log nyata di lapangan bisa lebih beragam.</li>',
          '<li>Empat dari lima fakta yang direncanakan hanya sebagian ditanam; kualitas data seragam antar stasiun, file, dan bulan, sehingga jawaban Q2 dan Q3 tidak informatif.</li>',
          '<li>Menit per langkah dan waktu tunggu sebelum ETL adalah asumsi penyusun; jam dihemat berlabel estimated.</li>',
          '<li>Baris bermasalah dikarantina, bukan diperbaiki otomatis; keputusan akhir ada pada manusia. Tidak ada uji statistik pola (dikerjakan di project lain).</li>',
          '<li>Cek silang Excel dihitung oleh LibreOffice, bukan Microsoft Excel. Dashboard belum di-deploy dan workflow GitHub Actions belum dijalankan; waktu proses diukur di satu mesin.</li>',
          '<li>Tidak ada masalah lisensi dataset (data buatan sendiri).</li></ul></div>')

evq = [("1", "rp1", "Data yang didapat", OK("Didapat"), f"{I(nfile)} file, {I(rows_read)} baris data, {I(r1.rows_inserted)} dimuat, {I(r1.rows_rejected)} dikarantina"),
       ("2", "rp2", "Business question terjawab?", OK(f"{len(QT)} dari {len(QT)}"), f"Semua terjawab ({npr['Utama']} Utama, {npr['Pendukung']} Pendukung, {npr['Tambahan']} Tambahan); {nw} dengan catatan ({wtxt})"),
       ("3", "rp3", "Dataset sesuai?", PART("Sebagian"), "Ukuran sesuai; empat dari lima fakta yang ditanam hanya sebagian"),
       ("4", "rp4", "Tools sesuai?", PART("Sesuai + penyesuaian"), "Tools inti dipakai; Pandera tidak; Streamlit belum di-deploy; Actions belum dijalankan"),
       ("5", "rp5", "Alur sesuai?", PART("Sesuai + tambahan"), "12 langkah dijalankan; langkah 3, 11, 12 sebagian"),
       ("6", "rp6", "Output tercapai?", PART(f"{cnt('Tercapai')} penuh, {cnt('Sebagian')} sebagian"), f"{cnt('Tercapai')} dari {len(nU)} output Utama penuh"),
       ("7", "rp7", "Kesimpulan", OK("Tersedia"), f"Hasil analisis, Impact, {len(crit)} kriteria sukses, rekomendasi, saran perbaikan, batasan")]
evq_html = '<div class="scroll"><table class="evq"><tr><th>No</th><th>Pertanyaan evaluasi</th><th>Verdict</th><th>Ringkasan</th></tr>' + "".join(
    f'<tr><td><span class="en">{n}</span></td><td><a href="#{h}">{t}</a></td><td>{v}</td><td>{s}</td></tr>' for n, h, t, v, s in evq) + "</table></div>"
H = lambda i, t, sm, body: f'\n<h2 id="rp{i}">{i}. {t}<small>{sm}</small></h2>\n{body}\n'
report = mk(
    '<div class="pane" id="report" data-tab="report" hidden>\n',
    f'<div class="callout g"><h4>Report Project versi 2: evaluasi hasil terhadap Design Project</h4><p>Halaman ini disusun sebagai 7 jawaban atas pertanyaan evaluasi. Tabel dan grafik dibuat otomatis dari hasil ETL, query SQL (DuckDB), dan cek silang pada data simulasi. '
    f'Hasil SQL dicek silang dengan pandas ({I(len(cx))} dari {I(len(cx))} pemeriksaan) dan dengan Excel ({I(len(rx))} dari {I(len(rx))}). Angka pada teks diaudit terhadap file di <code>project/results/</code>: @@AUDIT@@ angka diperiksa tanpa selisih. '
    'Semua angka bersumber dari data simulasi buatan sendiri dan menguji metode, bukan kondisi pabrik; angka dampak berlabel estimated. Rancangan lengkap ada di tab <a href="#design">Design Project</a>.</p></div>\n',
    evq_html,
    H(1, "Data yang berhasil didapatkan", "Isi data mentah, tabel di database, dan data hasil analisis", rp1),
    H(2, "Apakah business question terjawab?", f"{len(QT)} pertanyaan pada Design Project, dijawab dengan data", rp2),
    H(3, "Apakah dataset sesuai dengan Design Project?", "Perbandingan rancangan dengan realisasi", rp3),
    H(4, "Apakah tools yang digunakan sesuai?", "Perbandingan rancangan dengan eksekusi", rp4),
    H(5, "Apakah alur pengerjaan sesuai dengan Design Project?", f"{len(steps)} langkah rancangan vs yang dijalankan", rp5),
    H(6, "Apakah project output tercapai?", "Output pada Design Project, bagian 7", rp6),
    H(7, "Kesimpulan", "Hasil analisis, Impact, success criteria, rekomendasi, saran perbaikan, dan batasan", rp7),
    '</div>\n')

# ---------------------------------------------------------------- audit angka
STATIC = {str(i) for i in range(0, 21)} | {"30", "100", "80", "60", "0,05", "1E-9", "2.500", "7.000", "7.200", "37", "33260302", "2026", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12",
          "14", "15", "24", "40", "50", "95", "3", "4", "8", "31", "2–3", "5", "6", "0,001", "2020", "13", "0,000001"}
STATIC |= {f"{a}.{b}" for a in range(1, 10) for b in range(1, 10)}
n_tok, bad = audit(report, STATIC)
manual = [("seluruh CSV hasil terdokumentasi", not miss), ("fakta ditanam: 1 sesuai (fakta 4), 4 sebagian", gtc.hasil.tolist() == ["Sebagian", "Sebagian", "Sebagian", "Sesuai", "Sebagian"]),
          ("cek silang pandas, Excel, rekonsiliasi, uji run ulang semua PASS", (cx.status == "PASS").all() and (rx.status == "PASS").all() and (rc.status == "PASS").all() and (rr.status == "PASS").all()),
          ("dimuat + dikarantina = dibaca", int(r1.rows_inserted + r1.rows_rejected) == int(r1.rows_read) - 0 and int(rec_tot.rows_db + rec_tot.rows_quarantine) == int(rec_tot.rows_file)),
          ("semua masalah ditanam ditangani benar", (real.ditangani_benar == real.ditanam).all()), ("kualitas seragam (dasar catatan Q2, Q3)", dqf.dq_score.nunique() == 1 and dqm.reject_rate.nunique() == 1),
          ("jumlah pertanyaan = 13 (8 Utama, 4 Pendukung, 1 Tambahan)", len(QT) == 13 and npr == {"Utama": 8, "Pendukung": 4, "Tambahan": 1}),
          ("catatan hanya Q2, Q3, Q9, Q10, Q13", WARN == {2, 3, 9, 10, 13}), ("jumlah pertanyaan unik pada bagian 2 = 13", qn_uniq == list(range(1, 14))),
          ("langkah rancangan = 12", len(steps) == 12), ("kenaikan Reflow bulan ke-4 tidak ada", rf.loc["2026-06"] <= rf_other.max() + 1e-9),
          ("jam dihemat = (manual − ETL) × laporan per tahun ÷ 60", abs((ip.menit_manual - ip.menit_etl) * ip.laporan_per_tahun / 60 - ip.jam_dihemat_per_tahun) < 0.1)]
assert all(v for _, v in manual), [k for k, v in manual if not v]
if bad:
    print("TOKEN TIDAK TERDAFTAR:", bad)
    sys.exit(1)
report = report.replace("@@AUDIT@@", I(n_tok) + f" (ditambah {I(len(manual))} klaim manual)")

# ---------------------------------------------------------------- rakit halaman
v1 = (HERE / "page_v1.html").read_text(encoding="utf-8")
a = v1.index('<div class="pane" id="report"')
b = v1.index("</main>")
design_pane = v1[v1.index('<div class="pane" id="design"'):a]
nav_old = re.search(r'<nav aria-label="Project navigation">.*?</nav>', v1, re.S).group(0)
btn = lambda t: re.search(rf'<button type="button" class="tab[^"]*" data-t="{t}".*?</button>', nav_old, re.S).group(0)
design_links = re.search(r'<div class="links" data-tab="design">.*?</div>', nav_old, re.S).group(0)
report_links = ('<div class="links" data-tab="report" hidden>' + "".join(f'<a href="#rp{i}">{t}</a>' for i, t in
               enumerate(["Data", "Business Questions", "Dataset", "Tools", "Alur Kerja", "Project Output", "Kesimpulan"], 1)) + "</div>")
nav_new = f'<nav aria-label="Project navigation">{btn("design")}{btn("report")}{design_links}{report_links}</nav>'
css = (HERE / "report.css").read_text(encoding="utf-8")
html = v1[:a] + report + v1[b:]
html = html.replace(nav_old, nav_new)
i = html.rindex("</style>")
html = html[:i] + css + html[i:]
out = REPO / "design-and-report" / "index.html"
out.write_text(html, encoding="utf-8")
assert design_pane == html[html.index('<div class="pane" id="design"'):html.index('<div class="pane" id="report"')], "pane Design berubah"
print(f"index.html {len(html) / 1024:.0f} KB; {n_tok} angka diaudit; {len(manual)} klaim manual; pane Design identik")
