# Inventaris template

Tiga versi template, berganti per bulan (bukan per stasiun). Terdeteksi dari isi header, bukan dari nama file. Pemetaan kolom ada di `data/reference/column_mapping.yml`; template baru cukup menambah blok di file itu.

| Versi | Bulan | Header di baris | Ciri |
|---|---|---|---|
| v1 | Mar–Apr | 5 | Judul 4 baris di atas header; kolom Tanggal, OK, NG terpisah |
| v2 | Mei–Jun | 3 | Judul dengan sel gabungan, kolom Catatan, baris kosong di tengah data |
| v3 | Jul–Agu | 1 | Kolom `OK/NG` satu sel ("498/2"), baris TOTAL di bawah |

Jumlah per versi (dari `results/1-data-preparation/template_inventory.csv`): 20 file, 2.420 baris data masing-masing.
