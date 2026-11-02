# Aturan validasi

Baris yang gagal tidak dihapus: masuk tabel `rejected_rows` beserta aturan yang gagal dan baris mentahnya, lalu ditinjau manusia.

| Kode | Aturan | Perlakuan |
|---|---|---|
| R01 | Kolom wajib (tanggal, shift, model, operator, input, OK, NG) kosong atau tidak terbaca | Dikarantina |
| R02 | Shift bukan Shift 1 / Shift 2, atau model bukan Basic / Plus / Pro (setelah normalisasi) | Dikarantina |
| R03 | Jumlah negatif | Dikarantina |
| R04 | OK + NG tidak sama dengan input | Dikarantina |
| R05 | Kombinasi tanggal, stasiun, model, shift sudah ada (di database atau pada run yang sama) | Dikarantina |

Perbaikan format otomatis (dicatat di kolom `fixes`, baris tetap dimuat):
- `model_dinormalkan`: huruf besar/kecil, spasi, titik di ujung, awalan "Model ", ejaan (basik → Basic).
- `satuan_angka_dibuang`: angka bersatuan teks seperti "480 pcs".
- Template v3: kolom `OK/NG` satu sel ("498/2") dipecah menjadi OK dan NG.
- Baris kosong dan baris total/subtotal dilewati (dihitung di `rows_skipped`, tidak masuk data).

Alur koreksi: baris di `rejected_rows` dikoreksi manusia, lalu `reload_fixed` memvalidasi ulang dan memuatnya; `fixed_at` terisi. Baris yang masih gagal tetap di karantina.

Run ulang aman: kunci unik (tanggal, stasiun, model, shift) pada `production_log` dan `ON CONFLICT DO NOTHING` membuat run kedua memuat 0 baris baru.
