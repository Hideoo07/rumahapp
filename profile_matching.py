"""
profile_matching.py
Implementasi algoritma Profile Matching + bobot AHP untuk merekomendasikan rumah
sesuai profil/preferensi user. Ini adalah fungsi INTI sistem -- dipanggil oleh
app.py setiap kali user submit form.
"""
import json
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "rumah.db")
WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "ahp_weights.json")

# Tabel konversi GAP -> bobot nilai (sesuai proposal, Tabel Bobot Nilai GAP)
GAP_TO_BOBOT = {
    0: 5.0, 1: 4.5, -1: 4.0, 2: 3.5, -2: 3.0, 3: 2.5, -3: 2.0,
}


def gap_to_bobot(gap):
    """GAP di luar tabel (>3 atau <-3) -> nilai 1.0 (tidak cocok)."""
    if gap in GAP_TO_BOBOT:
        return GAP_TO_BOBOT[gap]
    return 1.0


def load_weights(kategori_pekerjaan):
    with open(WEIGHTS_PATH) as f:
        data = json.load(f)
    segmen = data["segmen"].get(kategori_pekerjaan, data["segmen"]["umum"])
    return segmen["bobot"]


def _score_harga(harga_rumah, harga_maks_user):
    """Skor 1-5: makin dekat/di bawah harga maksimal user, makin tinggi."""
    if harga_rumah <= harga_maks_user:
        # dalam budget -> skor tinggi, makin murah dari budget makin bagus (skala halus)
        rasio = harga_rumah / harga_maks_user if harga_maks_user > 0 else 1
        return 5 if rasio <= 0.9 else 4
    else:
        # di atas budget -> GAP negatif berdasarkan seberapa jauh melebihi
        selisih_persen = (harga_rumah - harga_maks_user) / harga_maks_user
        if selisih_persen <= 0.1:
            return 3
        elif selisih_persen <= 0.25:
            return 2
        else:
            return 1


def _score_lokasi(kota_rumah, kota_user):
    return 5 if kota_rumah.strip().lower() == kota_user.strip().lower() else 2


def _score_numeric_gap(actual, ideal):
    gap = actual - ideal
    return gap_to_bobot(gap)


def _score_kategori_pekerjaan(kategori_rumah, kategori_user):
    return 5 if kategori_rumah == kategori_user else 2.5


def _score_aksesibilitas(jarak_pusat_kota_km, jarak_maks_user_km):
    """
    Skor berdasarkan jarak rumah ke pusat kota vs preferensi maksimal user.
    Kalau data jarak tidak tersedia (rumah tanpa koordinat, atau kota belum
    ada di pusat_kota.csv), pakai skor netral (3) supaya kriteria ini tidak
    mendominasi maupun menjatuhkan skor total secara tidak adil.
    """
    if jarak_pusat_kota_km is None:
        return 3.0
    gap = round(jarak_maks_user_km - jarak_pusat_kota_km)
    return gap_to_bobot(gap)


def hitung_rekomendasi(user_profile, top_n=20):
    """
    user_profile: dict berisi
        harga_maks (int), kota (str), kamar_tidur_min (int),
        kamar_mandi_min (int), luas_bangunan_min (float), kategori_pekerjaan (str)
    """
    weights = load_weights(user_profile["kategori_pekerjaan"])

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM rumah").fetchall()
    conn.close()

    hasil = []
    for r in rows:
        skor = {}
        skor["harga"] = _score_harga(r["harga"], user_profile["harga_maks"])
        skor["lokasi"] = _score_lokasi(r["kota"], user_profile["kota"])
        skor["aksesibilitas"] = _score_aksesibilitas(
            r["jarak_pusat_kota_km"], user_profile.get("jarak_maks_pusat_kota_km", 10)
        )
        fasilitas_gap = (r["kamar_tidur"] - user_profile["kamar_tidur_min"])
        skor["fasilitas"] = gap_to_bobot(fasilitas_gap)
        skor["luas_bangunan"] = _score_numeric_gap(
            round(r["luas_bangunan"] / 10), round(user_profile["luas_bangunan_min"] / 10)
        )
        skor["kategori_pekerjaan"] = _score_kategori_pekerjaan(
            r["kategori_pekerjaan_cocok"], user_profile["kategori_pekerjaan"]
        )

        # Core factor: 2 kriteria dengan bobot AHP tertinggi untuk segmen ini
        # (mengikuti urutan prioritas per segmen: buruh->harga,lokasi;
        # ASN->lokasi,harga; pengusaha->aksesibilitas,harga)
        # Secondary factor: 4 kriteria sisanya.
        sorted_kriteria = sorted(weights, key=lambda k: weights[k], reverse=True)
        core = sorted_kriteria[:2]
        secondary = sorted_kriteria[2:]

        core_w_sum = sum(weights[k] for k in core)
        sec_w_sum = sum(weights[k] for k in secondary)

        ncf = sum(skor[k] * weights[k] for k in core) / core_w_sum if core_w_sum else 0
        nsf = sum(skor[k] * weights[k] for k in secondary) / sec_w_sum if sec_w_sum else 0

        # Proporsi core:secondary 60:40 sesuai proposal
        n_total = (0.6 * ncf) + (0.4 * nsf)

        hasil.append({
            "id": r["id"],
            "nama": r["nama"],
            "harga": r["harga"],
            "kota": r["kota"],
            "kecamatan": r["kecamatan"],
            "luas_bangunan": r["luas_bangunan"],
            "kamar_tidur": r["kamar_tidur"],
            "kamar_mandi": r["kamar_mandi"],
            "jenis_properti": r["jenis_properti"],
            "jarak_pusat_kota_km": round(r["jarak_pusat_kota_km"], 1) if r["jarak_pusat_kota_km"] is not None else None,
            "url": r["url"],
            "skor_detail": skor,
            "ncf": round(ncf, 3),
            "nsf": round(nsf, 3),
            "total_score": round(n_total, 3),
        })

    hasil.sort(key=lambda x: x["total_score"], reverse=True)
    return hasil[:top_n]
