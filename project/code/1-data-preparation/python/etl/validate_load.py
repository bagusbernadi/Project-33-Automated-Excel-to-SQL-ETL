"""Validasi, karantina, dan load ke DuckDB. Baris yang gagal tidak diperbaiki diam-diam: masuk rejected_rows beserta aturan yang gagal."""
import datetime as dt
import json
import time
from pathlib import Path

import pandas as pd

from .extract import extract_file, station_of
from .transform import transform_row

RULES = {
    "R01": "Kolom wajib kosong atau tidak terbaca (tanggal, shift, model, operator, input, OK, NG)",
    "R02": "Nilai di luar daftar (shift harus Shift 1 atau 2, model harus Basic, Plus, atau Pro)",
    "R03": "Jumlah negatif",
    "R04": "OK + NG tidak sama dengan input",
    "R05": "Kombinasi tanggal, stasiun, model, dan shift ganda",
}
REQUIRED = ["date", "shift", "model", "operator_id", "input_qty", "ok_qty", "ng_qty"]


def scalar(con, sql, params=None):
    """Satu nilai dari query (hasil dibaca habis agar koneksi DuckDB bebas)."""
    return con.execute(sql, params or []).fetchall()[0][0]


def ensure_schema(con, sql_path):
    con.execute(Path(sql_path).read_text(encoding="utf-8"))


def validate(rec):
    """Mengembalikan daftar (kode aturan, keterangan) yang gagal. Aturan R05 (kunci ganda) dicek terpisah oleh run_etl."""
    bad = []
    miss = [k for k in REQUIRED if rec.get(k) is None]
    if miss:
        bad.append(("R01", "kosong atau tidak terbaca: " + ", ".join(miss)))
    if rec.get("shift") is not None and rec["shift"] not in ("Shift 1", "Shift 2"):
        bad.append(("R02", f"shift {rec['shift']}"))
    if rec.get("model") is not None and rec["model"] not in ("Basic", "Plus", "Pro"):
        bad.append(("R02", f"model {rec['model']}"))
    q = [rec.get(k) for k in ("input_qty", "ok_qty", "ng_qty")]
    if all(v is not None for v in q):
        if min(q) < 0:
            bad.append(("R03", f"input={q[0]}, ok={q[1]}, ng={q[2]}"))
        if q[1] + q[2] != q[0]:
            bad.append(("R04", f"ok+ng={q[1] + q[2]} != input={q[0]}"))
    return bad


def _insert(con, table, df, cols):
    """INSERT ... ON CONFLICT DO NOTHING lewat DataFrame; mengembalikan jumlah baris baru."""
    if df.empty:
        return 0
    before = scalar(con, f"SELECT count(*) FROM {table}")
    con.register("df_in", df[cols])
    con.execute(f"INSERT INTO {table} ({', '.join(cols)}) SELECT {', '.join(cols)} FROM df_in ON CONFLICT DO NOTHING")
    con.unregister("df_in")
    return scalar(con, f"SELECT count(*) FROM {table}") - before


def run_etl(con, files, cfg):
    """Satu run ETL untuk semua file. Aman dijalankan ulang: kunci unik mencegah data ganda. Mengembalikan dict ringkasan run."""
    t0 = time.perf_counter()
    started = dt.datetime.now().replace(microsecond=0)
    run_id = scalar(con, "SELECT coalesce(max(run_id), 0) + 1 FROM etl_run_log")
    seen = {(d, s, m, sh): (sf, rn) for d, s, m, sh, sf, rn in con.execute("SELECT date, station, model, shift, source_file, row_no FROM production_log").fetchall()}
    stg, good, rej = [], [], []
    n_read = n_skip = 0
    for f in sorted(files, key=lambda p: Path(p).name):
        meta, rows = extract_file(f, cfg)
        n_read += meta["n_data"]
        n_skip += meta["n_blank"] + meta["n_summary"]
        for r in rows:
            raw_json = json.dumps(r["raw"], default=str, ensure_ascii=False, sort_keys=True)
            stg.append(dict(source_file=meta["source_file"], sheet=meta["sheet"], row_no=r["row_no"], seq=r["seq"],
                            template_version=meta["template_version"], raw_json=raw_json, run_id=run_id))
            rec, fixes = transform_row(r["raw"], cfg)
            bad = validate(rec)
            if not bad:
                key = (rec["date"], meta["station"], rec["model"], rec["shift"])
                owner = seen.get(key)
                if owner is not None and owner != (meta["source_file"], r["row_no"]):
                    bad.append(("R05", f"kunci sudah dimuat dari {owner[0]} baris {owner[1]}"))
                else:
                    seen[key] = (meta["source_file"], r["row_no"])
            if bad:
                for code, detail in bad:
                    rej.append(dict(source_file=meta["source_file"], row_no=r["row_no"], rule_failed=code, detail=detail, raw_value=raw_json, run_id=run_id))
            else:
                good.append(dict(date=rec["date"], shift=rec["shift"], station=meta["station"], model=rec["model"], operator_id=rec["operator_id"],
                                 input_qty=rec["input_qty"], ok_qty=rec["ok_qty"], ng_qty=rec["ng_qty"], source_file=meta["source_file"], row_no=r["row_no"],
                                 fixes=",".join(fixes) or None, run_id=run_id))
    _insert(con, "stg_raw_rows", pd.DataFrame(stg), ["source_file", "sheet", "row_no", "seq", "template_version", "raw_json", "run_id"])
    gdf = pd.DataFrame(good)
    ins = _insert(con, "production_log", gdf, ["date", "shift", "station", "model", "operator_id", "input_qty", "ok_qty", "ng_qty", "source_file", "row_no", "fixes", "run_id"])
    _insert(con, "rejected_rows", pd.DataFrame(rej), ["source_file", "row_no", "rule_failed", "detail", "raw_value", "run_id"])
    n_rej_rows = len({(r["source_file"], r["row_no"]) for r in rej})
    dur = round(time.perf_counter() - t0, 3)
    con.execute("INSERT INTO etl_run_log VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", [run_id, started, len(list(files)), n_read, n_skip, len(good), ins, n_rej_rows, dur])
    return dict(run_id=run_id, files=len(list(files)), rows_read=n_read, rows_skipped=n_skip, rows_valid=len(good), rows_inserted=ins, rows_rejected=n_rej_rows, duration_s=dur)


def reload_fixed(con, fixed, cfg):
    """Memuat ulang baris karantina yang sudah diperbaiki manusia. fixed: DataFrame (source_file, row_no, date, shift, model, operator_id, input_qty, ok_qty, ng_qty).
    Baris divalidasi dengan aturan yang sama; yang lolos masuk production_log dan rejected_rows.fixed_at diisi. Baris lain tidak disentuh."""
    run_id = scalar(con, "SELECT coalesce(max(run_id), 0) + 1 FROM etl_run_log")
    seen = {(d, s, m, sh) for d, s, m, sh in con.execute("SELECT date, station, model, shift FROM production_log").fetchall()}
    ok_rows, still_bad = [], 0
    for r in fixed.to_dict("records"):
        rec = {k: r[k] for k in REQUIRED}
        rec["date"] = pd.Timestamp(rec["date"]).date()
        st = station_of(r["source_file"], cfg)
        bad = validate(rec)
        key = (rec["date"], st, rec["model"], rec["shift"])
        if not bad and key in seen:
            bad = [("R05", "kunci sudah ada")]
        if bad:
            still_bad += 1
            continue
        seen.add(key)
        ok_rows.append(dict(rec, station=st, source_file=r["source_file"], row_no=int(r["row_no"]), fixes="diperbaiki_manual", run_id=run_id))
    df = pd.DataFrame(ok_rows)
    ins = _insert(con, "production_log", df, ["date", "shift", "station", "model", "operator_id", "input_qty", "ok_qty", "ng_qty", "source_file", "row_no", "fixes", "run_id"]) if len(df) else 0
    now = dt.datetime.now().replace(microsecond=0)
    for r in ok_rows:
        con.execute("UPDATE rejected_rows SET fixed_at = ? WHERE source_file = ? AND row_no = ?", [now, r["source_file"], r["row_no"]])
    return dict(reloaded=ins, still_rejected=still_bad)
