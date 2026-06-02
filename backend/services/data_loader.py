"""
Loads household data from an uploaded CSV or JSON file and normalises it
into the same DataFrame schema produced by data_generator.generate().

Required raw columns (matching the synthetic parquet schema):
  province, urban_rural, jml_anggota_keluarga, usia_kepala_keluarga,
  gender_kepala_keluarga, pendidikan_kepala_keluarga, status_pekerjaan_kk,
  sektor_pekerjaan_kk, jenis_lantai, jenis_dinding, jenis_atap,
  sumber_air_minum, fasilitas_bab, bahan_bakar_memasak, daya_listrik_terpasang,
  luas_lantai_per_kapita, kepemilikan_motor, kepemilikan_mobil,
  has_tv, has_fridge, has_mobile, aset_elektronik_inti,
  aset_lahan_pertanian, aset_peternakan, status_kepemilikan_rumah,
  dependency_ratio, electricity

Optional columns (will be defaulted if missing):
  desil_kesejahteraan_aktual, skor_pmt_konvensional, desil_pmt_konvensional,
  is_anomaly, anomaly_type, scenario, id, kecamatan
"""
import io
import json
import numpy as np
import pandas as pd

# ── Column definitions ────────────────────────────────────────────────────────

REQUIRED_COLS = [
    "province", "urban_rural",
    "jml_anggota_keluarga", "usia_kepala_keluarga", "gender_kepala_keluarga",
    "pendidikan_kepala_keluarga", "status_pekerjaan_kk", "sektor_pekerjaan_kk",
    "jenis_lantai", "jenis_dinding", "jenis_atap",
    "sumber_air_minum", "fasilitas_bab", "bahan_bakar_memasak",
    "daya_listrik_terpasang", "luas_lantai_per_kapita",
    "kepemilikan_motor", "kepemilikan_mobil",
    "has_tv", "has_fridge", "has_mobile",
    "aset_elektronik_inti", "aset_lahan_pertanian", "aset_peternakan",
    "status_kepemilikan_rumah", "dependency_ratio", "electricity",
]

# Defaults for columns that may be absent in real-world uploads
COL_DEFAULTS = {
    "desil_kesejahteraan_aktual": 0,    # 0 = unknown
    "skor_pmt_konvensional": 50.0,
    "desil_pmt_konvensional": 5,
    "is_anomaly": 0,
    "anomaly_type": "none",
    "scenario": "normal",
    "kecamatan": "Tidak Diketahui",
    "expenditure": 0,
}

# Template row for download — one realistic example
TEMPLATE_ROW = {
    "province": "Jawa Barat",
    "urban_rural": 1,
    "jml_anggota_keluarga": 4,
    "usia_kepala_keluarga": 42,
    "gender_kepala_keluarga": 1,
    "pendidikan_kepala_keluarga": 2,
    "status_pekerjaan_kk": 1,
    "sektor_pekerjaan_kk": 2,
    "jenis_lantai": 31,
    "jenis_dinding": 31,
    "jenis_atap": 31,
    "sumber_air_minum": 13,
    "fasilitas_bab": 12,
    "bahan_bakar_memasak": 3,
    "daya_listrik_terpasang": 900,
    "luas_lantai_per_kapita": 9.5,
    "kepemilikan_motor": 1,
    "kepemilikan_mobil": 0,
    "has_tv": 1,
    "has_fridge": 0,
    "has_mobile": 1,
    "aset_elektronik_inti": 2,
    "aset_lahan_pertanian": 0,
    "aset_peternakan": 0,
    "status_kepemilikan_rumah": 1,
    "dependency_ratio": 0.5,
    "electricity": 1,
    # Optional — include in template so users know they can provide these
    "desil_kesejahteraan_aktual": 3,
    "skor_pmt_konvensional": 52.0,
    "desil_pmt_konvensional": 4,
    "is_anomaly": 0,
    "scenario": "normal",
    "kecamatan": "Kec. Bandung Utara",
}


# ── Column encoding notes for user-facing template ────────────────────────────

ENCODING_NOTES = {
    "urban_rural": "1=Urban, 2=Rural",
    "gender_kepala_keluarga": "1=Laki-laki, 2=Perempuan",
    "pendidikan_kepala_keluarga": "0=Tidak Sekolah, 1=SD, 2=SMP, 3=SMA, 4=Perguruan Tinggi",
    "status_pekerjaan_kk": "0=Tidak Bekerja, 1=Informal, 2=Tidak Bekerja/Pengangguran, 3=Formal",
    "sektor_pekerjaan_kk": "0=Tidak Bekerja, 1=Pertanian, 2=Jasa, 3=Manufaktur, 4=Konstruksi",
    "jenis_lantai": "11=Tanah, 12=Bambu, 21/22=Kayu, 31-34=Semen/Keramik, 35/36=Marmer",
    "jenis_dinding": "11/12=Bambu, 21-24=Kayu, 31-34=Bata/Tembok",
    "jenis_atap": "11/12=Ijuk/Alang, 21=Asbes, 31-35=Seng/Genteng",
    "sumber_air_minum": "11/12=Air Kemasan, 13/14=Ledeng, 21=Sumur Bor, 31/32=Sumur Galian",
    "fasilitas_bab": "12=Sendiri Layak, 16/17=Sendiri Sederhana, 21=Bersama, 31=Umum, 51=Tidak Ada",
    "bahan_bakar_memasak": "1/2=Listrik/Gas Besar, 3/4=Gas 3kg, 5/6=Minyak Tanah, 7-11=Kayu",
    "daya_listrik_terpasang": "0=Tidak Ada, 450, 900, 1300, 2200 (VA)",
    "electricity": "1=Ada akses listrik, 0=Tidak ada",
    "kepemilikan_motor": "Jumlah motor (0, 1, 2, ...)",
    "kepemilikan_mobil": "Jumlah mobil (0, 1, 2, ...)",
    "has_tv": "1=Punya TV, 0=Tidak",
    "has_fridge": "1=Punya Kulkas, 0=Tidak",
    "has_mobile": "1=Punya HP, 0=Tidak",
    "aset_elektronik_inti": "Skor 0-4 (TV + Kulkas + PC + AC)",
    "aset_lahan_pertanian": "0=Tidak, 1=<0.5ha, 2=>0.5ha",
    "aset_peternakan": "0=Tidak, 1=Unggas, 2=Ruminansia Kecil, 3=Ruminansia Besar",
    "status_kepemilikan_rumah": "1=Milik Sendiri, 2=Kontrak/Sewa, 3=Bebas Sewa, 4=Dinas",
    "dependency_ratio": "Rasio anggota tidak produktif / total anggota (0.0-1.0)",
}


# ── Loaders ───────────────────────────────────────────────────────────────────

def load_csv(file_bytes: bytes) -> pd.DataFrame:
    """Parse CSV bytes into a DataFrame."""
    return pd.read_csv(io.BytesIO(file_bytes))


def load_json(file_bytes: bytes) -> pd.DataFrame:
    """Parse JSON bytes (array of objects) into a DataFrame."""
    data = json.loads(file_bytes.decode("utf-8"))
    if isinstance(data, list):
        return pd.DataFrame(data)
    elif isinstance(data, dict) and "records" in data:
        return pd.DataFrame(data["records"])
    else:
        raise ValueError("JSON must be an array of objects or {\"records\": [...]}")


# ── Validation & normalisation ────────────────────────────────────────────────

def validate_columns(df: pd.DataFrame) -> list[str]:
    """Return list of missing required columns."""
    return [c for c in REQUIRED_COLS if c not in df.columns]


def _compute_pmt_score(df: pd.DataFrame) -> pd.Series:
    """
    Simple PMT approximation based on Permensos No.5/2019 weights.
    Used when skor_pmt_konvensional is not provided in the upload.
    """
    FLOOR_WEIGHT  = {11: 0, 12: 10, 21: 20, 22: 20, 31: 40, 32: 40,
                     33: 60, 34: 60, 35: 80, 36: 80, 96: 15}
    WATER_WEIGHT  = {11: 90, 12: 90, 13: 80, 14: 80, 21: 70,
                     31: 50, 32: 50, 41: 40, 42: 40, 43: 50,
                     51: 30, 61: 20, 71: 10, 96: 30}
    TOILET_WEIGHT = {12: 90, 16: 70, 17: 70, 21: 50, 31: 30, 41: 20, 51: 0, 96: 40}
    LISTRIK_WEIGHT = {0: 0, 450: 20, 900: 50, 1300: 70, 2200: 90}

    score = pd.Series(50.0, index=df.index)
    score += df["jenis_lantai"].map(FLOOR_WEIGHT).fillna(20) * 0.25
    score += df["sumber_air_minum"].map(WATER_WEIGHT).fillna(40) * 0.15
    score += df["fasilitas_bab"].map(TOILET_WEIGHT).fillna(40) * 0.15
    score += df["daya_listrik_terpasang"].map(LISTRIK_WEIGHT).fillna(20) * 0.10
    score += df["luas_lantai_per_kapita"].clip(0, 30) / 30 * 100 * 0.20
    score += (df["kepemilikan_motor"] + df["kepemilikan_mobil"] * 3).clip(0, 10) / 10 * 100 * 0.05
    score += df["pendidikan_kepala_keluarga"] / 4 * 100 * 0.10
    return score.clip(0, 100)


def normalize_df(
    df: pd.DataFrame,
    province_id: str,
    scenario: str,
) -> pd.DataFrame:
    """
    Normalise an uploaded DataFrame to match the schema expected by predictor.run().
    - Fills missing optional columns with sensible defaults
    - Adds id, kecamatan, expenditure, and label columns
    - Computes PMT score if not provided
    """
    df = df.copy()

    # Ensure province column exists
    if "province" not in df.columns:
        df["province"] = province_id

    # Fill optional columns
    for col, default in COL_DEFAULTS.items():
        if col not in df.columns:
            df[col] = default

    # Force scenario to match upload parameter
    df["scenario"] = scenario

    # Compute PMT score & decile if not provided
    if "skor_pmt_konvensional" not in df.columns or df["skor_pmt_konvensional"].isna().all():
        df["skor_pmt_konvensional"] = _compute_pmt_score(df)
    if "desil_pmt_konvensional" not in df.columns or df["desil_pmt_konvensional"].isna().all():
        # Map 0-100 score to deciles 1-10 (higher score = higher decile = less poor)
        df["desil_pmt_konvensional"] = pd.cut(
            df["skor_pmt_konvensional"],
            bins=[0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 101],
            labels=list(range(1, 11)),
            include_lowest=True,
        ).astype(int)

    # Add id if missing
    if "id" not in df.columns:
        code = province_id[:2].upper()
        df["id"] = [f"UP-{code}-{i:04d}" for i in range(len(df))]

    # Add expenditure (proxy: luas_lantai * 100000 if not present)
    if "expenditure" not in df.columns or df["expenditure"].eq(0).all():
        df["expenditure"] = (
            df.get("pengeluaran_per_kapita", df["luas_lantai_per_kapita"] * 80000)
            * df["jml_anggota_keluarga"]
        ).astype(int)

    # Label helpers used by data_generator.to_records()
    EDU_LABELS    = {0: "Tidak Sekolah", 1: "SD", 2: "SMP", 3: "SMA", 4: "Perguruan Tinggi"}
    SECTOR_LABELS = {1: "Pertanian", 2: "Jasa", 3: "Manufaktur", 4: "Konstruksi", 0: "Tidak Bekerja"}
    GENDER_LABELS = {1: "L", 2: "P"}
    FLOOR_LABELS  = {11: "Tanah", 12: "Bambu", 21: "Kayu", 22: "Kayu",
                     31: "Semen", 32: "Semen", 33: "Keramik", 34: "Keramik",
                     35: "Marmer", 36: "Marmer", 96: "Lainnya"}
    WATER_LABELS  = {11: "Air Kemasan", 12: "Air Kemasan", 13: "Ledeng", 14: "Ledeng",
                     21: "Sumur Bor", 31: "Sumur Galian", 32: "Sumur Galian",
                     41: "Mata Air", 42: "Mata Air", 43: "Sumur",
                     51: "Air Hujan", 61: "Mata Air Tak Terlindung",
                     62: "Air Permukaan", 71: "Air Sungai", 72: "Air Danau/Kolam", 96: "Lainnya"}
    STATUS_LABELS = {"none": "normal", "phk": "phk_risk", "bencana": "disaster_risk"}

    df["edu_label"]    = df["pendidikan_kepala_keluarga"].map(EDU_LABELS).fillna("Lainnya")
    df["sector_label"] = df["sektor_pekerjaan_kk"].map(SECTOR_LABELS).fillna("Lainnya")
    df["gender_label"] = df["gender_kepala_keluarga"].map(GENDER_LABELS).fillna("L")
    df["floor_label"]  = df["jenis_lantai"].map(FLOOR_LABELS).fillna("Lainnya")
    df["water_label"]  = df["sumber_air_minum"].map(WATER_LABELS).fillna("Lainnya")
    df["status_label"] = df["anomaly_type"].map(STATUS_LABELS).fillna("normal")

    return df


# ── Template generator ────────────────────────────────────────────────────────

def get_template_csv() -> str:
    """Return a CSV string with header + one example row + encoding comments."""
    df = pd.DataFrame([TEMPLATE_ROW])
    csv_buf = io.StringIO()
    # Add encoding notes as commented header lines
    for col, note in ENCODING_NOTES.items():
        csv_buf.write(f"# {col}: {note}\n")
    csv_buf.write("#\n# Hapus baris komentar (#) sebelum upload.\n#\n")
    df.to_csv(csv_buf, index=False)
    return csv_buf.getvalue()
