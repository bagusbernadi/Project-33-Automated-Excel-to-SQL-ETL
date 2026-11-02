-- Empat tabel project 33. Data mentah masuk staging dulu; baris lolos validasi masuk production_log; baris gagal masuk rejected_rows.
CREATE TABLE IF NOT EXISTS stg_raw_rows (
    source_file      VARCHAR  NOT NULL,
    sheet            VARCHAR  NOT NULL,
    row_no           INTEGER  NOT NULL,            -- nomor baris di file Excel
    seq              INTEGER  NOT NULL,            -- urutan baris data (tanpa judul, header, baris kosong, ringkasan)
    template_version VARCHAR  NOT NULL,
    raw_json         VARCHAR  NOT NULL,            -- sel mentah apa adanya
    run_id           INTEGER  NOT NULL,
    PRIMARY KEY (source_file, sheet, row_no)
);
CREATE TABLE IF NOT EXISTS production_log (
    date         DATE     NOT NULL,
    shift        VARCHAR  NOT NULL CHECK (shift IN ('Shift 1', 'Shift 2')),
    station      VARCHAR  NOT NULL,
    model        VARCHAR  NOT NULL CHECK (model IN ('Basic', 'Plus', 'Pro')),
    operator_id  VARCHAR  NOT NULL,
    input_qty    INTEGER  NOT NULL CHECK (input_qty >= 0),
    ok_qty       INTEGER  NOT NULL CHECK (ok_qty >= 0),
    ng_qty       INTEGER  NOT NULL CHECK (ng_qty >= 0),
    source_file  VARCHAR  NOT NULL,
    row_no       INTEGER  NOT NULL,
    fixes        VARCHAR,                          -- perbaikan format otomatis (mis. model_dinormalkan), kosong bila tidak ada
    run_id       INTEGER  NOT NULL,
    PRIMARY KEY (date, station, model, shift),     -- kunci unik: run ulang tidak menggandakan data
    CHECK (ok_qty + ng_qty = input_qty)
);
CREATE TABLE IF NOT EXISTS rejected_rows (
    source_file  VARCHAR  NOT NULL,
    row_no       INTEGER  NOT NULL,
    rule_failed  VARCHAR  NOT NULL,
    detail       VARCHAR,
    raw_value    VARCHAR  NOT NULL,                -- baris mentah dalam JSON
    run_id       INTEGER  NOT NULL,
    fixed_at     TIMESTAMP,                        -- terisi bila baris diperbaiki lalu dimuat ulang
    PRIMARY KEY (source_file, row_no, rule_failed)
);
CREATE TABLE IF NOT EXISTS etl_run_log (
    run_id        INTEGER PRIMARY KEY,
    started_at    TIMESTAMP NOT NULL,
    files_read    INTEGER NOT NULL,
    rows_read     INTEGER NOT NULL,                -- baris data (tanpa judul, header, baris kosong, ringkasan)
    rows_skipped  INTEGER NOT NULL,                -- baris kosong dan baris ringkasan yang dilewati
    rows_valid    INTEGER NOT NULL,                -- lolos validasi pada run ini
    rows_inserted INTEGER NOT NULL,                -- benar-benar baru masuk production_log
    rows_rejected INTEGER NOT NULL,
    duration_s    DOUBLE NOT NULL
);
