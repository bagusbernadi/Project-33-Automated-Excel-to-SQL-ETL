"""Unit test untuk aturan transform dan validasi, uji run ulang, uji karantina, dan rekonsiliasi kecil. Jalankan dari folder project/: python -m pytest tests -q"""
import datetime as dt

import duckdb
import openpyxl
import pandas as pd
import pytest

from common import MAPPING_YML, SQL_PREP
from etl.extract import extract_file, load_config, station_of
from etl.transform import norm_model, norm_shift, parse_date, parse_int, transform_row
from etl.validate_load import ensure_schema, reload_fixed, run_etl, validate

CFG = load_config(MAPPING_YML)


# ---------------------------------------------------------------- transform
@pytest.mark.parametrize("raw,expected", [(dt.datetime(2026, 3, 2), dt.date(2026, 3, 2)), ("02/03/26", dt.date(2026, 3, 2)), ("03-Aug-26", dt.date(2026, 8, 3)),
                                          ("2026/08/03", dt.date(2026, 8, 3)), ("2026-08-03", dt.date(2026, 8, 3)), ("bukan tanggal", None), (None, None)])
def test_parse_date(raw, expected):
    assert parse_date(raw, CFG["date_formats"]) == expected


@pytest.mark.parametrize("raw,expected", [(5, (5, False)), (5.0, (5, False)), ("480 pcs", (480, True)), (" 12 ", (12, False)), ("-3", (-3, False)), ("None", (None, False)), (None, (None, False)), (4.5, (None, False))])
def test_parse_int(raw, expected):
    assert parse_int(raw) == expected


@pytest.mark.parametrize("raw,expected", [("Pro", "Pro"), ("PRO.", "Pro"), ("pro", "Pro"), ("Model Pro", "Pro"), ("basik", "Basic"), ("plus ", "Plus"), ("xyz", None), (None, None)])
def test_norm_model(raw, expected):
    assert norm_model(raw, CFG["model_aliases"])[0] == expected


def test_norm_shift():
    assert norm_shift("shift 2")[0] == "Shift 2" and norm_shift("Shift 3")[0] is None and norm_shift(None)[0] is None


def test_transform_v3_single_cell():
    rec, fixes = transform_row(dict(date="03-Aug-26", shift="Shift 1", model="Basic", operator_id="OP07", input_qty="500 pcs", ok_ng="498/2"), CFG)
    assert (rec["input_qty"], rec["ok_qty"], rec["ng_qty"]) == (500, 498, 2) and fixes == ["satuan_angka_dibuang"]
    rec, _ = transform_row(dict(date="03-Aug-26", shift="Shift 1", model="Basic", operator_id="OP07", input_qty=500, ok_ng="None/2"), CFG)
    assert rec["ok_qty"] is None


# ---------------------------------------------------------------- validasi
def rec(**kw):
    base = dict(date=dt.date(2026, 3, 2), shift="Shift 1", model="Pro", operator_id="OP01", input_qty=100, ok_qty=95, ng_qty=5)
    return {**base, **kw}


def test_validate_clean():
    assert validate(rec()) == []


@pytest.mark.parametrize("kw,code", [(dict(shift=None), "R01"), (dict(ok_qty=None), "R01"), (dict(model="Max"), "R02"), (dict(ng_qty=-5, ok_qty=105), "R03"), (dict(ok_qty=90), "R04")])
def test_validate_rules(kw, code):
    assert code in [c for c, _ in validate(rec(**kw))]


# ---------------------------------------------------------------- extract per template + load
def make_file(path, tpl, rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    if tpl == "v1":
        ws["A1"] = "LOG PRODUKSI - Reflow Soldering"
        ws.append([]); ws.append([]); ws.append([])
        ws.append(["Tanggal", "Shift", "Model", "Operator", "Input", "OK", "NG"])
        for r in rows:
            ws.append([r[0], r[1], r[2], r[3], r[4], r[5], r[6]])
    elif tpl == "v2":
        ws["A1"] = "Reflow Soldering - Laporan Output"; ws.merge_cells("A1:H1"); ws.append([])
        ws.append(["Tgl", "Shift", "Model", "Operator", "Input", "OK", "NG", "Catatan"])
        for n, r in enumerate(rows):
            ws.append([r[0].strftime("%d/%m/%y"), r[1], r[2], r[3], r[4], r[5], r[6], ""])
            if n == 1:
                ws.append([])
    else:
        ws.append(["Date", "Shift", "Model", "Operator", "Input", "OK/NG"])
        for r in rows:
            ws.append([r[0].strftime("%d-%b-%y"), r[1], r[2], r[3], r[4], f"{r[5]}/{r[6]}"])
        ws.append(["TOTAL", None, None, None, sum(r[4] for r in rows), None])
    wb.save(path)


ROWS = [(dt.date(2026, 3, 2), "Shift 1", "Basic", "OP01", 100, 98, 2), (dt.date(2026, 3, 2), "Shift 2", "Plus", "OP02", 90, 88, 2), (dt.date(2026, 3, 3), "Shift 1", "Pro", "OP01", 80, 79, 1)]


@pytest.fixture
def files(tmp_path):
    out = []
    for i, tpl in enumerate(("v1", "v2", "v3"), start=1):
        p = tmp_path / f"log_03_reflow_2026-0{i + 2}.xlsx"
        make_file(p, tpl, [(r[0].replace(month=i + 2),) + r[1:] for r in ROWS])
        out.append(p)
    return out


def test_extract_detects_template_and_skips(files):
    got = {}
    for p in files:
        meta, rows = extract_file(p, CFG)
        got[meta["template_version"]] = (meta["n_data"], meta["n_blank"], meta["n_summary"], meta["station"])
    assert got == {"v1": (3, 0, 0, "Reflow Soldering"), "v2": (3, 1, 0, "Reflow Soldering"), "v3": (3, 0, 1, "Reflow Soldering")}


def test_station_from_filename():
    assert station_of("log_10_packaging_2026-08.xlsx", CFG) == "Packaging"
    with pytest.raises(ValueError):
        station_of("random.xlsx", CFG)


@pytest.fixture
def con():
    c = duckdb.connect(":memory:")
    ensure_schema(c, SQL_PREP / "01_schema.sql")
    return c


def test_run_twice_no_duplicates(con, files):
    r1, r2 = run_etl(con, files, CFG), run_etl(con, files, CFG)
    n = con.execute("SELECT count(*) FROM production_log").fetchall()[0][0]
    assert (r1["rows_inserted"], r2["rows_inserted"], n) == (9, 0, 9) and r1["rows_rejected"] == r2["rows_rejected"] == 0


def test_bad_rows_go_to_quarantine(con, tmp_path):
    p = tmp_path / "log_03_reflow_2026-03.xlsx"
    bad = ROWS + [ROWS[0], (dt.date(2026, 3, 4), "Shift 1", "Pro", "OP01", 100, 90, 5), (dt.date(2026, 3, 4), "Shift 2", "Pro", "OP01", 100, 105, -5)]
    make_file(p, "v1", bad)
    r = run_etl(con, [p], CFG)
    rules = sorted(x[0] for x in con.execute("SELECT rule_failed FROM rejected_rows").fetchall())
    assert r["rows_inserted"] == 3 and r["rows_rejected"] == 3 and rules == ["R03", "R04", "R05"]


def test_reconciliation_small(con, files):
    run_etl(con, files, CFG)
    assert con.execute("SELECT sum(input_qty), sum(ok_qty), sum(ng_qty) FROM production_log").fetchall()[0] == (3 * sum(r[4] for r in ROWS), 3 * sum(r[5] for r in ROWS), 3 * sum(r[6] for r in ROWS))


def test_reload_fixed_row(con, tmp_path):
    p = tmp_path / "log_03_reflow_2026-03.xlsx"
    make_file(p, "v1", ROWS + [(dt.date(2026, 3, 4), "Shift 1", "Pro", "OP01", 100, 90, 5)])
    run_etl(con, [p], CFG)
    before = con.execute("SELECT count(*) FROM production_log").fetchall()[0][0]
    rn = con.execute("SELECT row_no FROM rejected_rows").fetchall()[0][0]
    fixed = pd.DataFrame([dict(source_file=p.name, row_no=rn, date="2026-03-04", shift="Shift 1", model="Pro", operator_id="OP01", input_qty=100, ok_qty=95, ng_qty=5)])
    assert reload_fixed(con, fixed, CFG) == dict(reloaded=1, still_rejected=0)
    assert con.execute("SELECT count(*) FROM production_log").fetchall()[0][0] == before + 1
    assert con.execute("SELECT count(*) FROM rejected_rows WHERE fixed_at IS NOT NULL").fetchall()[0][0] == 1
