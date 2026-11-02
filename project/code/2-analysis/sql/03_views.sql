-- View analitik project 33. Dibaca oleh 03_run_queries.py. Semua angka kualitas data berasal dari tabel hasil ETL (staging, production_log, rejected_rows).
CREATE OR REPLACE VIEW dim_station AS
SELECT * FROM (VALUES
  ('01', 'Solder Paste Printing', 1), ('02', 'Component Placement', 2), ('03', 'Reflow Soldering', 3), ('04', 'AOI Inspection', 4),
  ('05', 'Board Test (ICT)', 5), ('06', 'Screen Assembly', 6), ('07', 'Housing Assembly', 7), ('08', 'Final Inspection', 8),
  ('09', 'Functional Test', 9), ('10', 'Packaging', 10)) AS t(stn_no, station, ord);

-- satu baris per baris data di file Excel beserta nasibnya (bersih, diperbaiki format, ditolak)
CREATE OR REPLACE VIEW v_data_rows AS
SELECT s.source_file, s.row_no, s.seq, s.template_version,
       regexp_extract(s.source_file, 'log_(\d\d)_', 1)      AS stn_no,
       regexp_extract(s.source_file, '(\d{4}-\d{2})\.xlsx', 1) AS month,
       CASE WHEN r.source_file IS NOT NULL THEN 'ditolak'
            WHEN p.source_file IS NULL THEN 'tidak dimuat'
            WHEN p.fixes IS NULL THEN 'bersih'
            ELSE 'diperbaiki format' END AS status,
       p.fixes
FROM stg_raw_rows s
LEFT JOIN (SELECT DISTINCT source_file, row_no FROM rejected_rows) r ON r.source_file = s.source_file AND r.row_no = s.row_no
LEFT JOIN production_log p ON p.source_file = s.source_file AND p.row_no = s.row_no;

CREATE OR REPLACE VIEW v_dq_station AS
SELECT d.ord, d.station, count(*) AS rows_total,
       count(*) FILTER (WHERE v.status = 'bersih') AS rows_clean,
       count(*) FILTER (WHERE v.status = 'diperbaiki format') AS rows_fixed,
       count(*) FILTER (WHERE v.status = 'ditolak') AS rows_rejected
FROM v_data_rows v JOIN dim_station d USING (stn_no) GROUP BY d.ord, d.station;

CREATE OR REPLACE VIEW v_dq_file AS
SELECT v.source_file, d.station, v.month, any_value(v.template_version) AS template_version, count(*) AS rows_total,
       count(*) FILTER (WHERE v.status = 'bersih') AS rows_clean,
       count(*) FILTER (WHERE v.status = 'diperbaiki format') AS rows_fixed,
       count(*) FILTER (WHERE v.status = 'ditolak') AS rows_rejected
FROM v_data_rows v JOIN dim_station d USING (stn_no) GROUP BY v.source_file, d.station, v.month;

CREATE OR REPLACE VIEW v_dq_month AS
SELECT month, any_value(template_version) AS template_version, count(*) AS rows_total,
       count(*) FILTER (WHERE status = 'bersih') AS rows_clean,
       count(*) FILTER (WHERE status = 'diperbaiki format') AS rows_fixed,
       count(*) FILTER (WHERE status = 'ditolak') AS rows_rejected
FROM v_data_rows GROUP BY month;

CREATE OR REPLACE VIEW v_prod_month AS
SELECT p.station, d.ord, p.model, strftime(p.date, '%Y-%m') AS month,
       sum(p.input_qty)::BIGINT AS input_qty, sum(p.ok_qty)::BIGINT AS ok_qty, sum(p.ng_qty)::BIGINT AS ng_qty,
       sum(p.ok_qty) * 1.0 / sum(p.input_qty)::BIGINT AS yield, sum(p.ng_qty) * 1.0 / sum(p.input_qty)::BIGINT AS ng_rate, count(*) AS n_rows
FROM production_log p JOIN dim_station d ON d.station = p.station GROUP BY p.station, d.ord, p.model, month;

CREATE OR REPLACE VIEW v_prod_daily AS
SELECT date, sum(input_qty)::BIGINT AS input_qty, sum(ok_qty)::BIGINT AS ok_qty, sum(ng_qty)::BIGINT AS ng_qty,
       sum(ok_qty) * 1.0 / sum(input_qty)::BIGINT AS yield, sum(ng_qty) * 1.0 / sum(input_qty)::BIGINT AS ng_rate, count(*) AS n_rows
FROM production_log GROUP BY date;

CREATE OR REPLACE VIEW v_prod_daily_station AS
SELECT p.station, d.ord, p.date, sum(p.input_qty)::BIGINT AS input_qty, sum(p.ng_qty)::BIGINT AS ng_qty, sum(p.ng_qty) * 1.0 / sum(p.input_qty)::BIGINT AS ng_rate
FROM production_log p JOIN dim_station d ON d.station = p.station GROUP BY p.station, d.ord, p.date;
