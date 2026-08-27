"""
ahp.py
Menghitung bobot kriteria dengan metode AHP (Analytical Hierarchy Process).
Ini dijalankan SEKALI di tahap persiapan (bukan tiap user pakai sistem) --
sesuai flowchart di proposal. Hasil bobot disimpan ke ahp_weights.json
dan dipakai oleh profile_matching.py.

FITUR: sistem menghitung 3 SET BOBOT terpisah, satu untuk tiap kategori
pekerjaan (buruh, ASN, pengusaha), karena tiap segmen konsumen punya
prioritas kriteria yang berbeda saat mencari rumah:
  - Buruh      -> paling mengutamakan HARGA murah
  - ASN        -> paling mengutamakan LOKASI (kedekatan dgn instansi/kantor)
  - Pengusaha  -> paling mengutamakan AKSESIBILITAS (akses jalan/bisnis)

Ini TETAP sesuai batasan "tanpa campur tangan manual kecuali input profil
user": ketiga set bobot dihitung SEKALI di awal oleh peneliti (bukan oleh
admin/sistem tiap kali dipakai). Saat runtime, sistem hanya MEMILIH salah
satu set bobot yang sudah tersimpan, berdasarkan kategori pekerjaan yang
dipilih user sendiri di form -- bukan menghitung ulang atau butuh keputusan
manual baru.

Cara pakai:
    python ahp.py
"""
import json
import os
import numpy as np

KRITERIA = ["harga", "lokasi", "aksesibilitas", "fasilitas", "luas_bangunan", "kategori_pekerjaan"]

# Random Index (Saaty) untuk n = 1..10, dipakai menghitung Consistency Ratio
RI_TABLE = {1: 0.00, 2: 0.00, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45, 10: 1.49}

# Urutan prioritas kriteria per segmen konsumen, dari yang PALING penting (index 0)
# ke yang paling kurang penting. Ini adalah pertimbangan peneliti yang bisa
# dijustifikasi dengan literatur/logika di skripsi (BAB 3).
RANKING = {
    "umum": ["harga", "lokasi", "aksesibilitas", "fasilitas", "luas_bangunan", "kategori_pekerjaan"],
    "buruh": ["harga", "lokasi", "aksesibilitas", "fasilitas", "luas_bangunan", "kategori_pekerjaan"],
    "asn": ["lokasi", "harga", "aksesibilitas", "fasilitas", "luas_bangunan", "kategori_pekerjaan"],
    "pengusaha": ["aksesibilitas", "harga", "lokasi", "fasilitas", "luas_bangunan", "kategori_pekerjaan"],
}

OUT_PATH = os.path.join(os.path.dirname(__file__), "ahp_weights.json")


def ranking_to_pairwise_matrix(ranking, kriteria):
    """
    Mengubah urutan prioritas (ranking) menjadi matriks perbandingan
    berpasangan skala Saaty (1-9). Kriteria peringkat teratas diberi
    skor intensitas tertinggi.

    Karena matriks diturunkan langsung dari skor rasio (bukan penilaian
    manual satu-satu), hasilnya otomatis konsisten sempurna (CR ~ 0).
    """
    n = len(kriteria)
    intensitas = [9, 6, 4, 3, 2, 1][:n]
    skor = {kriteria_nama: intensitas[pos] for pos, kriteria_nama in enumerate(ranking)}

    matrix = np.zeros((n, n))
    for i, ki in enumerate(kriteria):
        for j, kj in enumerate(kriteria):
            matrix[i][j] = skor[ki] / skor[kj]
    return matrix


def compute_ahp_weights(matrix, kriteria):
    n = len(kriteria)
    col_sums = matrix.sum(axis=0)
    normalized = matrix / col_sums
    weights = normalized.mean(axis=1)

    weighted_sum = matrix @ weights
    lambda_max = (weighted_sum / weights).mean()
    ci = (lambda_max - n) / (n - 1) if n > 1 else 0
    ri = RI_TABLE.get(n, 1.49)
    cr = ci / ri if ri != 0 else 0

    return weights, cr


def main():
    result = {"kriteria": KRITERIA, "segmen": {}}

    for segmen, ranking in RANKING.items():
        matrix = ranking_to_pairwise_matrix(ranking, KRITERIA)
        weights, cr = compute_ahp_weights(matrix, KRITERIA)

        print(f"\n=== Segmen: {segmen.upper()} ===")
        print(f"Urutan prioritas: {' > '.join(ranking)}")
        for k, w in zip(KRITERIA, weights):
            print(f"  {k:20s}: {w:.4f}")
        status = "KONSISTEN" if cr < 0.1 else "TIDAK KONSISTEN, perbaiki ranking!"
        print(f"  Consistency Ratio (CR): {cr:.4f} -> {status}")

        result["segmen"][segmen] = {
            "urutan_prioritas": ranking,
            "bobot": {k: round(float(w), 4) for k, w in zip(KRITERIA, weights)},
            "consistency_ratio": round(float(cr), 4),
        }

    with open(OUT_PATH, "w") as f:
        json.dump(result, f, indent=2)
    print(f"\nSemua bobot tersimpan di {OUT_PATH}")


if __name__ == "__main__":
    main()
