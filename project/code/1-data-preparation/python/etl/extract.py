"""Extract: membaca satu file log Excel, mengenali versi template, mencari baris header, melewati judul, baris kosong, dan baris ringkasan."""
import re
from pathlib import Path

import openpyxl
import yaml


def load_config(path):
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def station_of(filename, cfg):
    m = re.match(r"log_(\d\d)_", Path(filename).name)
    if not m or m.group(1) not in cfg["stations"]:
        raise ValueError(f"nama file tidak dikenali: {filename}")
    return cfg["stations"][m.group(1)]


def detect_template(header, cfg):
    names = {str(h).strip() for h in header if h is not None}
    for ver, spec in cfg["templates"].items():
        need = spec.get("detect_header_has", [])
        if need and all(n in names for n in need):
            return ver
    for ver, spec in reversed(list(cfg["templates"].items())):      # cadangan: semua kolom dikenal
        if names and names <= set(spec["columns"]):
            return ver
    raise ValueError(f"template tidak dikenali: {sorted(names)}")


def extract_file(path, cfg):
    """Mengembalikan (meta, rows). rows: dict per baris data: row_no (nomor baris Excel), seq (urutan baris data), raw (kolom kanonik -> nilai mentah)."""
    path = Path(path)
    ws = openpyxl.load_workbook(path, data_only=True).active
    all_rows = list(ws.iter_rows(values_only=True))
    hdr_i = next((i for i, r in enumerate(all_rows[:12]) if r and r[0] is not None and str(r[0]).strip().lower() in cfg["header_first_cells"]), None)
    if hdr_i is None:
        raise ValueError(f"baris header tidak ditemukan: {path.name}")
    header = all_rows[hdr_i]
    ver = detect_template(header, cfg)
    cmap = cfg["templates"][ver]["columns"]
    cols = {j: cmap[str(h).strip()] for j, h in enumerate(header) if h is not None and str(h).strip() in cmap}
    meta = dict(source_file=path.name, sheet=ws.title, template_version=ver, station=station_of(path, cfg), header_row=hdr_i + 1,
                merged_cells=len(ws.merged_cells.ranges), n_blank=0, n_summary=0, n_title=hdr_i)
    rows, seq = [], 0
    for i in range(hdr_i + 1, len(all_rows)):
        r = all_rows[i]
        if all(c is None or (isinstance(c, str) and not c.strip()) for c in r):
            meta["n_blank"] += 1
            continue
        first = str(r[0]).strip().lower() if r[0] is not None else ""
        if first in cfg["skip_first_cells"]:
            meta["n_summary"] += 1
            continue
        rows.append(dict(row_no=i + 1, seq=seq, raw={c: r[j] for j, c in cols.items()}))
        seq += 1
    meta["n_data"] = len(rows)
    return meta, rows
