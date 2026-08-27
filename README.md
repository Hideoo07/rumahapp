# Sistem Rekomendasi Pembelian Rumah Hunian
Metode: AHP + Profile Matching

## Update Terbaru (Penting)
Core Factor dan Secondary Factor pada `profile_matching.py` sekarang **dinamis
mengikuti 2 kriteria berbobot tertinggi per segmen** (bukan selalu tetap
harga+lokasi seperti versi sebelumnya). Ini memperbaiki inkonsistensi antara
konsep tiga-set-bobot-AHP-per-segmen dengan implementasi Core/Secondary Factor
yang lama. Dampaknya: hasil rekomendasi untuk segmen **buruh dan ASN tidak
berubah** (Core mereka tetap harga+lokasi), tapi hasil untuk segmen
**pengusaha berubah** (Core sekarang harga+aksesibilitas, sesuai prioritas
segmen tersebut). Angka di BAB IV skripsi sudah disesuaikan dengan versi kode
ini -- jangan pakai versi profile_matching.py yang lebih lama.

## Struktur Proyek
```
rumah_app/
├── app.py                 # Aplikasi Flask (routing, form, hasil)
├── profile_matching.py    # Algoritma inti: GAP, Core/Secondary Factor, ranking
├── ahp.py                 # Hitung bobot kriteria AHP (dijalankan sekali di awal)
├── ahp_weights.json       # Hasil bobot AHP (dibuat otomatis oleh ahp.py)
├── init_db.py             # Import data scraping (xlsx) -> database SQLite
├── data/
│   ├── data_original.xlsx # Data hasil scraping OLX (1.186 data valid)
│   └── rumah.db            # Database SQLite (dibuat otomatis oleh init_db.py)
├── templates/
│   ├── index.html          # Form input profil user
│   └── result.html         # Halaman hasil rekomendasi
└── requirements.txt
```

## Cara Menjalankan (di laptop kamu)

1. Buat virtual environment (opsional tapi disarankan):
   ```
   python -m venv venv
   venv\Scripts\activate      # Windows
   source venv/bin/activate   # Mac/Linux
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Buat database dari data scraping (jalankan sekali saja, atau setiap kali data diperbarui):
   ```
   python init_db.py
   ```

4. (Opsional) Hitung ulang bobot AHP kalau kamu mengubah matriks perbandingan berpasangan di `ahp.py`:
   ```
   python ahp.py
   ```

5. Jalankan aplikasi:
   ```
   python app.py
   ```

6. Buka browser ke: http://127.0.0.1:5000

## Yang PERLU kamu sesuaikan sebelum sidang

1. **Bobot AHP per segmen konsumen di `ahp.py` (dict `RANKING`)** — sistem sekarang
   menghitung 3 SET bobot terpisah (buruh, ASN, pengusaha), masing-masing dari urutan
   prioritas kriteria yang berbeda:
     - Buruh &rarr; harga paling diutamakan
     - ASN &rarr; lokasi paling diutamakan
     - Pengusaha &rarr; aksesibilitas paling diutamakan

   Urutan ini masih pertimbangan awal, silakan sesuaikan/perkuat dengan argumen di
   BAB 3 skripsimu (misal dengan mengutip studi perilaku konsumen properti). Jalankan
   ulang `python ahp.py` setelah diubah, lalu jalankan ulang `python app.py`.

   CATATAN: karena matriks perbandingan dihasilkan otomatis dari urutan prioritas
   (bukan input manual satu-satu), Consistency Ratio (CR) selalu 0 -- ini justru
   nilai tambah untuk dijelaskan ke penguji: proses bebas dari inkonsistensi
   penilaian manual.

2. **Batas kategori pekerjaan di `init_db.py` (fungsi `kategori_harga`)** — ambang
   Rp300 juta dan Rp800 juta masih ASUMSI, dipakai sebagai kriteria tambahan
   "kelayakan harga" terpisah dari bobot prioritas di atas. Sesuaikan dengan
   justifikasi yang kamu tulis di proposal, lalu jalankan ulang `python init_db.py`.

3. **Skor aksesibilitas** di `profile_matching.py` sekarang dihitung dari JARAK
   rumah ke pusat kota (bukan lagi nilai netral tetap), TAPI baru aktif kalau
   kamu mengisi data koordinat pusat kota:
   - Buka `data/pusat_kota_template.csv` -- sudah berisi 61 nama kota/kabupaten
     PERSIS sesuai yang ada di datasetmu (tidak perlu ketik ulang nama kota).
   - Isi kolom `lat` dan `lon` untuk tiap kota (koordinat kantor bupati/walikota,
     atau titik tengah kota, cukup akurat sampai 2-3 desimal).
   - Simpan file sebagai `data/pusat_kota.csv` (boleh isi sebagian dulu kalau
     waktu terbatas -- kota yang belum diisi otomatis dapat skor netral, sistem
     tidak akan error).
   - Jalankan ulang `python init_db.py`. Sistem akan otomatis menghitung jarak
     tiap rumah ke pusat kotanya (pakai rumus Haversine dari koordinat rumah
     hasil scraping) dan menampilkan berapa rumah yang berhasil dihitung.
   - CATATAN: sekitar 34% data rumah (401 dari 1.186) tidak punya koordinat
     lat/lon dari hasil scraping OLX, jadi jaraknya tidak bisa dihitung untuk
     rumah-rumah itu -- otomatis dapat skor netral juga. Ini boleh disebut
     sebagai keterbatasan sistem di BAB 4/5.

## Untuk Bab 4 (Pengujian)

- Jalankan beberapa skenario input berbeda lewat form, screenshot hasilnya.
- Untuk membuktikan perhitungan sistem benar, ambil 1 contoh rumah dari hasil,
  lalu hitung manual GAP/Core Factor/Secondary Factor di Excel, bandingkan
  dengan `ncf`, `nsf`, dan `total_score` yang ditampilkan sistem.
