"""
init_db.py
Mengimpor data hasil scraping (data_original.xlsx) ke database SQLite.
Jalankan sekali di awal: python init_db.py
"""
import pandas as pd
import numpy as np
import sqlite3
import os

SOURCE_XLSX = os.path.join(os.path.dirname(__file__), "data", "data_original.xlsx")
DB_PATH = os.path.join(os.path.dirname(__file__), "data", "rumah.db")


def main():
    print(f"Membaca data dari {SOURCE_XLSX} ...")
    df = pd.read_excel(SOURCE_XLSX)

    # Rename kolom supaya konsisten & mudah dipakai di kode (snake_case)
    df = df.rename(columns={
        "Product Name": "nama",
        "Price_Clean": "harga",
        "Luas bangunan": "luas_bangunan",
        "Kamar_tidur_clean": "kamar_tidur",
        "Kamar_Mandi_clean": "kamar_mandi",
        "Jenis_Properti": "jenis_properti",
        "Kecamatan": "kecamatan",
        "Kota_Kab": "kota",
        "Provinsi": "provinsi",
        "URL": "url",
    })

    # Kolom yang dipakai sistem. Score_Harga/Score_Luas_Bangunan/Score_Fasilitas
    # dari scraping lama TIDAK dipakai langsung -- karena skor GAP harus dihitung
    # ulang terhadap preferensi tiap user, bukan skor statis per rumah.
    keep_cols = [
        "nama", "harga", "luas_bangunan", "kamar_tidur", "kamar_mandi",
        "jenis_properti", "kecamatan", "kota", "provinsi", "url", "lat", "lon",
    ]
    df = df[keep_cols]

    # Bersihkan data: buang baris tanpa harga/luas (data tidak valid untuk dihitung)
    before = len(df)
    df = df.dropna(subset=["harga", "luas_bangunan"])
    df = df[(df["harga"] > 0) & (df["luas_bangunan"] > 0)]
    after = len(df)
    print(f"Baris awal: {before}, setelah cleaning: {after} (dibuang {before - after})")

    # Kategori pekerjaan yang "cocok" untuk tiap rumah, berdasarkan rentang harga.
    # Ini dipakai sebagai salah satu kriteria Profile Matching (lihat profile_matching.py).
    def kategori_harga(harga):
        if harga <= 300_000_000:
            return "buruh"
        elif harga <= 500_000_000:
            return "asn"
        else:
            return "pengusaha"

    df["kategori_pekerjaan_cocok"] = df["harga"].apply(kategori_harga)

    # Hitung jarak tiap rumah ke pusat kota/kabupaten (untuk kriteria Aksesibilitas).
    # Butuh file data/pusat_kota.csv (kota, lat, lon) -- lihat data/pusat_kota_template.csv
    # sebagai contoh format. Kalau file belum ada, jarak diisi None dan sistem akan
    # memakai skor netral untuk kriteria aksesibilitas (lihat profile_matching.py).
    pusat_kota_path = os.path.join(os.path.dirname(__file__), "data", "pusat_kota.csv")
    if os.path.exists(pusat_kota_path):
        pusat_kota = pd.read_csv(pusat_kota_path)
        pusat_kota = pusat_kota.dropna(subset=["lat", "lon"])
        pusat_kota = pusat_kota.rename(columns={"lat": "pk_lat", "lon": "pk_lon"})
        df = df.merge(pusat_kota[["kota", "pk_lat", "pk_lon"]], on="kota", how="left")

        def hitung_jarak_km(row):
            if pd.isna(row["lat"]) or pd.isna(row["lon"]) or pd.isna(row.get("pk_lat")) or pd.isna(row.get("pk_lon")):
                return None
            R = 6371.0
            lat1, lon1, lat2, lon2 = map(np.radians, [row["lat"], row["lon"], row["pk_lat"], row["pk_lon"]])
            dlat, dlon = lat2 - lat1, lon2 - lon1
            a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
            return R * 2 * np.arcsin(np.sqrt(a))

        df["jarak_pusat_kota_km"] = df.apply(hitung_jarak_km, axis=1)
        df = df.drop(columns=["pk_lat", "pk_lon"])

        # Filter outlier: jarak >100km ke pusat kota sendiri hampir pasti data
        # koordinat rumah yang keliru dari hasil scraping (bukan kesalahan
        # koordinat pusat kota), sehingga diperlakukan sebagai data tidak
        # tersedia agar tidak merusak perhitungan kriteria aksesibilitas.
        OUTLIER_THRESHOLD_KM = 100
        outlier_mask = df["jarak_pusat_kota_km"] > OUTLIER_THRESHOLD_KM
        n_outlier = outlier_mask.sum()
        if n_outlier > 0:
            print(f"Catatan: {n_outlier} data memiliki jarak >{OUTLIER_THRESHOLD_KM}km ke pusat kotanya "
                  f"sendiri (indikasi koordinat rumah keliru pada hasil scraping). "
                  f"Jarak untuk data ini diset kosong (skor netral) agar tidak bias.")
            df.loc[outlier_mask, "jarak_pusat_kota_km"] = None

        n_ok = df["jarak_pusat_kota_km"].notna().sum()
        print(f"Jarak ke pusat kota terhitung untuk {n_ok}/{len(df)} rumah "
              f"(sisanya tidak punya koordinat rumah dan/atau kota belum ada di pusat_kota.csv).")
    else:
        df["jarak_pusat_kota_km"] = None
        print(f"CATATAN: {pusat_kota_path} belum ada -- kriteria aksesibilitas sementara "
              f"pakai skor netral. Isi data/pusat_kota_template.csv lalu simpan sebagai "
              f"pusat_kota.csv untuk mengaktifkan perhitungan jarak.")

    conn = sqlite3.connect(DB_PATH)
    df.to_sql("rumah", conn, if_exists="replace", index=True, index_label="id")
    conn.close()
    print(f"Selesai! {after} data rumah disimpan ke {DB_PATH}")


if __name__ == "__main__":
    main()
