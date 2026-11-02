"""Transform: menyeragamkan tanggal, shift, model, dan angka. Nilai yang tidak terbaca menjadi None dan ditangkap oleh validasi, bukan ditebak."""
import datetime as dt
import re

SHIFT_RE = re.compile(r"^shift\s*([12])$", re.I)
INT_RE = re.compile(r"^\s*(-?\d+)\s*(?:pcs|unit)?\s*$", re.I)


def parse_date(v, formats):
    if v is None:
        return None
    if isinstance(v, dt.datetime):
        return v.date()
    if isinstance(v, dt.date):
        return v
    if isinstance(v, (int, float)) and 20000 < v < 80000:          # angka serial Excel
        return (dt.datetime(1899, 12, 30) + dt.timedelta(days=float(v))).date()
    s = str(v).strip()
    for f in formats:
        try:
            return dt.datetime.strptime(s, f).date()
        except ValueError:
            pass
    return None


def parse_int(v):
    """Mengembalikan (nilai, diubah). 'diubah' True bila ada satuan teks yang dibuang (mis. '480 pcs')."""
    if v is None:
        return None, False
    if isinstance(v, bool):
        return None, False
    if isinstance(v, (int, float)):
        return (int(v), False) if float(v) == int(v) else (None, False)
    m = INT_RE.match(str(v))
    if not m:
        return None, False
    return int(m.group(1)), not re.fullmatch(r"\s*-?\d+\s*", str(v))


def norm_model(v, aliases):
    if v is None or not str(v).strip():
        return None, False
    s = re.sub(r"^model\s+", "", str(v).strip().lower()).strip(" .")
    out = aliases.get(s)
    return out, (out is not None and out != str(v))


def norm_shift(v):
    if v is None or not str(v).strip():
        return None, False
    m = SHIFT_RE.match(str(v).strip())
    return (f"Shift {m.group(1)}", f"Shift {m.group(1)}" != str(v)) if m else (None, False)


def transform_row(raw, cfg):
    """raw: kolom kanonik -> nilai mentah. Mengembalikan (record, fixes). Kolom yang gagal dibaca bernilai None."""
    fixes, rec = [], {}
    rec["date"] = parse_date(raw.get("date"), cfg["date_formats"])
    rec["shift"], ch = norm_shift(raw.get("shift"))
    rec["model"], chm = norm_model(raw.get("model"), cfg["model_aliases"])
    if chm:
        fixes.append("model_dinormalkan")
    rec["operator_id"] = (str(raw["operator_id"]).strip() or None) if raw.get("operator_id") is not None else None
    rec["input_qty"], c1 = parse_int(raw.get("input_qty"))
    if "ok_ng" in raw:                                               # template v3: satu sel "OK/NG"
        parts = str(raw["ok_ng"]).split("/") if raw.get("ok_ng") is not None else []
        a, b = (parts + [None, None])[:2] if len(parts) == 2 else (None, None)
        rec["ok_qty"], c2 = parse_int(a)
        rec["ng_qty"], c3 = parse_int(b)
    else:
        rec["ok_qty"], c2 = parse_int(raw.get("ok_qty"))
        rec["ng_qty"], c3 = parse_int(raw.get("ng_qty"))
    if c1 or c2 or c3:
        fixes.append("satuan_angka_dibuang")
    return rec, fixes
