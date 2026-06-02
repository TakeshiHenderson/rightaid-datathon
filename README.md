# RightAid — ML-PMT Dashboard

> **Dicoding × Microsoft Elevate Datathon 2026** · Tema: Ekonomi Digital & Inklusi Keuangan

RightAid adalah platform analitik berbasis web untuk mendeteksi **mis-targeting** dalam program bantuan sosial Indonesia. Platform ini membandingkan metode Proxy Means Testing (PMT) konvensional dengan model Machine Learning (XGBoost) yang mendeteksi rumah tangga yang seharusnya menerima bansos tetapi tidak terdata (*exclusion error*), dan sebaliknya.

---

## Struktur Repositori

```
elevate-model/
├── model/              # Pipeline data sintetis + training model ML
├── backend/            # FastAPI REST API (wraps trained models)
├── frontend/           # Static web dashboard (HTML + CSS + JS)
├── .gitignore
└── README.md           ← kamu di sini
```

---

## Prasyarat

| Tool | Versi minimum |
|------|--------------|
| Python | 3.10+ |
| pip | 23+ |
| Git | 2.x |
| (Opsional) Node.js | 18+ (hanya untuk serve frontend via `npx serve`) |

Tidak ada perbedaan setup antara **Windows** dan **Linux/macOS** — semua path di kode sudah menggunakan `pathlib.Path` yang cross-platform.

---

## Quickstart (Local Dev)

### 1. Clone repo

```bash
git clone https://github.com/<your-org>/elevate-model.git
cd elevate-model
```

### 2. Buat virtual environment

```bash
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (CMD)
.venv\Scripts\activate.bat
```

### 3. Install semua dependencies

```bash
# Model pipeline + backend sekaligus
pip install -r backend/requirements.txt
pip install xgboost scikit-learn pandas numpy pyarrow shap scipy matplotlib
```

### 4. Konfigurasi environment backend

```bash
cp backend/.env.example backend/.env
```

Buka `backend/.env` dan isi nilai berikut:

```env
SECRET_KEY=<generate dengan: python -c "import secrets; print(secrets.token_hex(32))">
RIGHTAID_USERS_JSON=[{"email":"guest@rightaid.id","password":"guest123","name":"Guest Analyst","role":"guest"}]

# Azure OpenAI — opsional (policy brief pakai template fallback kalau kosong)
AZURE_OPENAI_ENDPOINT=
AZURE_OPENAI_KEY=
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# JANGAN isi path di bawah ini — biarkan ter-comment agar config.py
# resolve otomatis relatif terhadap root repo (works di Windows & Linux)
# PROVINCE_CONFIG_PATH=
# MODEL_ELIGIBILITY_PATH=
# MODEL_ANOMALY_PATH=
```

> **Catatan cross-platform:** Jangan uncomment atau isi `PROVINCE_CONFIG_PATH`, `MODEL_ELIGIBILITY_PATH`, `MODEL_ANOMALY_PATH` di `.env`. `backend/config.py` sudah resolve path ini secara otomatis menggunakan `pathlib.Path` sehingga bekerja di Windows maupun Linux tanpa perlu diubah.

### 5. Generate model (jika belum ada file `.pkl`)

```bash
# Dari root repo
python model/rerun_pipeline.py
```

Ini akan menghasilkan:
- `model/output/xgboost_eligibility_v3.pkl` — model eligibility (AUC: 0.9797)
- `model/output/xgboost_anomaly_v2.pkl` — model anomaly detection (AUC: 0.9987)
- `model/output/rightaid_processed.parquet` — dataset dengan fitur engineered
- `model/output/evaluation_report_v3.json` — full metrics

> Proses ini memakan waktu ~2 menit (1.14M rows, training XGBoost).

### 6. Jalankan backend

```bash
# Dari dalam folder backend/
cd backend
python -m uvicorn main:app --reload --port 8000
```

Backend berjalan di `http://localhost:8000`.  
Swagger UI: `http://localhost:8000/docs`

### 7. Jalankan frontend

```bash
# Dari folder frontend/ — cara paling sederhana:
cd frontend
python -m http.server 5500

# Atau menggunakan npx serve (Node.js):
npx serve .
```

Buka browser: `http://localhost:5500`

Login dengan:
- Email: `guest@rightaid.id`
- Password: `guest123`

---

## Alur Penggunaan (User Flow)

```
Login → Dashboard (stats nasional) → Analysis (pilih provinsi + skenario)
     → Generate Data / Upload CSV → Predict → Lihat SHAP → Policy Brief
```

1. **Dashboard** — Menampilkan statistik kemiskinan nasional, tren error, dan perbandingan PMT vs ML dari API backend.
2. **Analysis** — Pilih skenario (Baseline / PHK Massal / Pasca-Bencana), klik **Generate & Predict** untuk menjalankan model secara langsung, atau **Upload CSV** dari data nyata.
3. **Data Viewer** — Tabel rumah tangga dengan kolom desil PMT vs desil ML. Bila ada sesi aktif, data dimuat dari API.
4. **Policy Brief** — Generate dokumen rekomendasi kebijakan otomatis (via Azure OpenAI atau template fallback).

---

## Deployment ke Azure

Karena arsitektur memisahkan `backend/` dan `model/`, backend **wajib di-deploy menggunakan Docker** agar semua file terangkut.

### 1. Frontend (Azure Static Web Apps)
Paling mudah dideploy langsung dari GitHub atau via CLI dari root repo:
```bash
az staticwebapp create --name rightaid-web --resource-group <Nama-RG> \
  --source . --app-location "frontend" --login-with-github
```

### 2. Backend (Web App for Containers)
Backend harus dibangun sebagai Docker image agar memuat file model(`.pkl`) dari folder `model/output/`.

```bash
# 1. Build & Push Image ke Azure Container Registry (ACR)
az acr create --resource-group <Nama-RG> --name rightaidregistry --sku Basic
az acr build --registry rightaidregistry --image rightaid-api:v1 -f backend/Dockerfile .

# 2. Buat App Service Plan (Linux)
az appservice plan create --name rightaid-plan --resource-group <Nama-RG> --is-linux --sku B1

# 3. Deploy API menggunakan image dari ACR
az webapp create --resource-group <Nama-RG> --plan rightaid-plan --name rightaid-api \
  --container-image-name rightaidregistry.azurecr.io/rightaid-api:v1
```
*Catatan: Tambahkan konfigurasi `.env` ke App Service Configuration di portal Azure.*

---

## Upload Data Nyata (CSV / JSON)

Selain generate data sintetis, platform mendukung upload data rumah tangga nyata:

1. Di halaman **Analysis**, klik **Download Template** untuk mendapatkan format CSV yang benar.
2. Isi data sesuai kolom template (lihat [skema kolom](backend/services/data_loader.py)).
3. Klik **Upload & Predict** — data akan divalidasi, dinormalisasi, lalu dijalankan melalui model ML.

**Endpoint upload:**
```
POST /api/upload
Content-Type: multipart/form-data
  file        : file .csv atau .json
  province_id : kode provinsi (contoh: "JB" atau "Jawa Barat")
  scenario    : "normal" | "phk" | "bencana"
```

---

## API Endpoints

Semua endpoint kecuali `/health` dan `POST /api/auth/login` memerlukan JWT Bearer token.

| Method | Path | Deskripsi |
|--------|------|-----------|
| `GET` | `/health` | Health check |
| `POST` | `/api/auth/login` | Login — returns JWT token |
| `GET` | `/api/stats/national` | Statistik kemiskinan nasional |
| `GET` | `/api/stats/trend` | Tren exclusion/inclusion error bulanan |
| `GET` | `/api/model/comparison` | PMT vs ML metrics |
| `GET` | `/api/provinces` | List 38 provinsi dengan statistik |
| `POST` | `/api/generate` | Generate dataset sintetis |
| `POST` | `/api/upload` | Upload CSV/JSON data nyata |
| `GET` | `/api/upload/template` | Download template CSV |
| `GET` | `/api/data/{session_id}` | Paginated dataset view |
| `GET` | `/api/data/{session_id}/export` | Export dataset as CSV |
| `POST` | `/api/predict/{session_id}` | Jalankan ML inference |
| `GET` | `/api/shap/{session_id}/{record_id}` | SHAP explanation per record |
| `POST` | `/api/policy-brief` | Generate policy brief (Azure OpenAI / template fallback) |

**Contoh curl (Linux/macOS):**
```bash
# 1. Login
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"guest@rightaid.id","password":"guest123"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")

# 2. Generate 500 RT di Jawa Barat, skenario PHK
curl -s -X POST http://localhost:8000/api/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"province_id":"JB","scenario":"phk","anomaly_pct":0.15,"n":500}'

# 3. Predict (ganti SESSION_ID dengan hasil dari step 2)
curl -s -X POST http://localhost:8000/api/predict/SESSION_ID \
  -H "Authorization: Bearer $TOKEN"
```

---

## Struktur Detail

Untuk dokumentasi lebih lanjut per komponen, lihat:

- [`model/README.md`](model/README.md) — pipeline data sintetis, training, dan evaluasi model
- [`backend/README.md`](backend/README.md) — arsitektur backend, services, dan Docker

---

## Hasil Model

| Task | Model | AUC | F1 |
|------|-------|-----|----|
| Eligibility (bottom 40%) | XGBoost | **0.9797** | **0.9035** |
| Anomaly detection | XGBoost | **0.9987** | **0.9279** |

**PMT vs ML (exclusion error):**
- PMT konvensional: **6.96%** eligible household terlewat
- ML-PMT: **3.21%** eligible household terlewat (↓ 54%)
- Anomaly exclusion error: PMT **70.7%** → ML **1.21%**

---

## Tim

| Nama | Peran |
|------|-------|
| Sean | Data Science & ML Lead |
| *(anggota 2)* | Azure & Backend Engineer |
| *(anggota 3)* | Frontend & Visualization Engineer |

---

## Catatan

- Data yang digunakan adalah data **sintetis** yang dibangun dari distribusi agregat BPS Susenas — bukan data individu yang bersifat rahasia.
- Platform mendukung upload data nyata (CSV/JSON) untuk dianalisis langsung oleh model.
- Frontend berjalan **offline-first**: jika backend tidak tersedia, semua halaman jatuh ke data dummy EkoData.
