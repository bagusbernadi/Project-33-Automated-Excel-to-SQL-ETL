# Definisi dan asumsi

Ditetapkan sebelum analisis. Data simulasi.

## Metrik
- **Yield** = OK / input. **NG rate** = NG / input. Jumlah dari baris produksi yang lolos validasi (`production_log`).
- **Baris data** = baris di file Excel selain judul, header, baris kosong, dan baris total.
- **Load rate** = baris dimuat / baris data. **Reject rate** = baris dikarantina / baris data.
- **DQ score** = baris bersih (tanpa perbaikan dan tanpa karantina) / baris data, dalam persen. `rows_fixed` = dimuat setelah perbaikan format.
- **Spike harian**: NG rate harian satu stasiun dengan z-score > 3 terhadap rata-rata stasiun itu.

## Rekonsiliasi
Per file: jumlah baris, input, OK, NG pada file harus sama dengan jumlah di `production_log` ditambah `rejected_rows`. Dihitung lewat SQL, pandas, dan Excel (dihitung ulang oleh LibreOffice, bukan Microsoft Excel).

## Asumsi dampak (estimated, bukan data aktual)
| Langkah | Menit manual | Menit setelah ETL |
|---|---|---|
| Kumpulkan file | 25 | 1 |
| Salin dan gabung | 40 | 0 |
| Rapikan format | 35 | 0 |
| Cek salah ketik | 30 | 5 |
| Hitung KPI | 20 | 0 |
| Buat grafik | 20 | 2 |

- Menit setelah ETL ditambah durasi run yang terukur (±1,3 detik).
- 8 laporan per bulan (skenario 4 dan 12 ditampilkan); jam dihemat = (menit manual − menit ETL) × laporan per tahun / 60.
- Waktu tunggu laporan: 24 jam manual, 15 menit setelah ETL (asumsi).
- Angka waktu manual adalah asumsi penyusun, bukan hasil pengukuran di pabrik.
