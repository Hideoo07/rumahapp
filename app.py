from flask import Flask, render_template, request
from profile_matching import hitung_rekomendasi
import sqlite3
import os

app = Flask(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "data", "rumah.db")


def get_daftar_kota():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT DISTINCT kota FROM rumah ORDER BY kota").fetchall()
    conn.close()
    return [r[0] for r in rows]


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html", daftar_kota=get_daftar_kota())


@app.route("/rekomendasi", methods=["POST"])
def rekomendasi():
    user_profile = {
        "harga_maks": int(request.form["harga_maks"]),
        "kota": request.form["kota"],
        "kamar_tidur_min": int(request.form["kamar_tidur_min"]),
        "kamar_mandi_min": int(request.form.get("kamar_mandi_min", 1)),
        "luas_bangunan_min": float(request.form["luas_bangunan_min"]),
        "jarak_maks_pusat_kota_km": float(request.form.get("jarak_maks_pusat_kota_km", 10)),
        "kategori_pekerjaan": request.form["kategori_pekerjaan"],
    }

    hasil = hitung_rekomendasi(user_profile, top_n=20)
    return render_template("result.html", hasil=hasil, profile=user_profile)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
