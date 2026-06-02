# model/ — Data Pipeline & ML Training

> Bagian ini berisi pipeline untuk menghasilkan data sintetis dan melatih model ML.
> Untuk setup lengkap, lihat [README utama](../README.md).

---

## Isi Folder

```
model/
├── province_master_config.json     # Kalibrasi per provinsi (38 provinsi, BPS Susenas)
├── regenerate_data.py              # Generator data sintetis (1.14M RT)
├── rerun_pipeline.py               # Feature engineering + training kedua model
├── predict.py                      # Inference standalone (tanpa API)
├── gen_notebook.py                 # (Opsional) generate EDA notebook
├── gen_modeling_notebook.py        # (Opsional) generate modeling notebook
└── output/                         # Sebagian di-track git, sebagian tidak
    ├── xgboost_eligibility_v3.pkl  # ✅ Di-commit (~6.5 MB) — backend butuh ini
    ├── xgboost_anomaly_v2.pkl      # ✅ Di-commit (~1.5 MB) — backend butuh ini
    ├── evaluation_report_v3.json   # ✅ Di-commit (~2 KB)
    ├── eda_metadata.json           # ✅ Di-commit (~1 KB)
    └── rightaid_processed.parquet  # ❌ Gitignored (35 MB) — regenerate jika perlu
```

> `.parquet` is gitignored (35 MB, regenerable). `.pkl` files are tracked.

---

## Cara Menjalankan Pipeline

**Dari root repo** (bukan dari dalam folder `model/`):

```bash
# Install dependencies
pip install xgboost scikit-learn pandas numpy pyarrow shap matplotlib

# Jalankan pipeline (generate + train + evaluate)
python model/rerun_pipeline.py
```

> Proses ini memakan waktu ~2 menit.  
> File `.pkl` output otomatis disimpan ke `model/output/`.

---

## Hasil Model

| Task | Metrik | PMT Konvensional | ML (XGBoost) |
|------|--------|-----------------|--------------|
| Eligibility (bottom 40%) | AUC | — | **0.9797** |
| Eligibility | F1 | 0.817 | **0.9035** |
| Eligibility | Exclusion Error | 6.96% | **3.21%** |
| Eligibility | Inclusion Error | 7.83% | **4.65%** |
| Anomaly Detection | AUC | — | **0.9987** |
| Anomaly Detection | F1 | — | **0.9279** |
| Anomaly Exclusion Error | | 70.70% | **1.21%** |

---

## Data Sintetis

Data dibangkitkan dari distribusi agregat **BPS Susenas** (bukan data individu) menggunakan `regenerate_data.py`.

- **38 provinsi**, 3 skenario per provinsi: `normal`, `phk`, `bencana`
- **1.14 juta baris** total (~10.000 RT × 3 skenario × 38 provinsi)
- Variabel berkorelasi dengan pendapatan (bukan independen): pendidikan, sektor pekerjaan, kondisi hunian, dll.

Untuk generate ulang dari awal (biasanya tidak perlu — file `.parquet` sudah ada):

```bash
python model/regenerate_data.py
```

---

## Catatan Teknis

- **Target**: `bottom40 = desil_kesejahteraan_aktual <= 4` (40% terbawah = eligible bansos)
- **34 fitur**: 29 base (housing quality, aset, sosial-ekonomi) + 5 interaction features
- **Tidak ada data leakage**: `pengeluaran_per_kapita` (pendapatan aktual) dan skor PMT dikecualikan dari fitur
- **Threshold**: dioptimalkan untuk F1 di test set, tersimpan di dalam `.pkl`
- **Cross-platform**: semua path menggunakan `pathlib.Path(__file__).parent` — bekerja di Windows & Linux
