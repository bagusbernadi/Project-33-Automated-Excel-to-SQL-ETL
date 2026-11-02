# Kamus data

## production_log (data bersih, kunci unik: date, station, model, shift)
| Kolom | Tipe | Arti |
|---|---|---|
| date | DATE | Tanggal produksi |
| shift | VARCHAR | Shift 1 / Shift 2 |
| station | VARCHAR | Satu dari 10 stasiun perakitan (dari nomor di nama file) |
| model | VARCHAR | Basic / Plus / Pro |
| operator_id | VARCHAR | ID operator |
| input_qty, ok_qty, ng_qty | INTEGER | Jumlah unit; OK + NG = input |
| source_file, row_no | | Asal baris di file Excel |
| fixes | VARCHAR | Perbaikan format otomatis, kosong bila tidak ada |
| run_id | INTEGER | Run ETL yang memuat |

## stg_raw_rows
Sel mentah apa adanya (`raw_json`) per baris data, dengan `template_version` dan `seq`. Kunci: source_file, sheet, row_no.

## rejected_rows
`source_file`, `row_no`, `rule_failed` (R01–R05), `detail`, `raw_value` (JSON), `run_id`, `fixed_at`.

## etl_run_log
Satu baris per run: `files_read`, `rows_read`, `rows_skipped`, `rows_valid`, `rows_inserted`, `rows_rejected`, `duration_s`.
