# backend/ — RightAid FastAPI Backend

> REST API yang membungkus model ML dan menyediakan data untuk frontend.
> Untuk setup lengkap, lihat [README utama](../README.md).

---

## Struktur

```
backend/
├── main.py              # FastAPI app + semua route handler
├── auth.py              # JWT authentication
├── config.py            # Pydantic-settings (baca dari .env)
├── models.py            # Pydantic request/response schemas
├── session_store.py     # In-memory session store (dataset hasil generate)
├── requirements.txt     # Python dependencies
├── Dockerfile           # Dibangun dari repo root
├── .env.example         # Template environment variables
└── services/
    ├── data_generator.py  # Generate data sintetis per-provinsi
    ├── data_loader.py     # Validasi & normalisasi upload CSV/JSON
    ├── predictor.py       # Inference model + PMT benchmark
    ├── shap_service.py    # SHAP explanation per record
    └── policy_brief.py    # Azure OpenAI policy brief (dengan template fallback)
```

---

## Setup

```bash
# Dari root repo
pip install -r backend/requirements.txt

# Konfigurasi
cp backend/.env.example backend/.env
# Edit backend/.env — minimal: SECRET_KEY dan RIGHTAID_USERS_JSON
```

### Variabel `.env` penting

| Variabel | Keterangan | Wajib? |
|----------|-----------|--------|
| `SECRET_KEY` | JWT signing secret | **Ya** |
| `RIGHTAID_USERS_JSON` | JSON array users `[{"email":…,"password":…,"name":…,"role":…}]` | **Ya** |
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint | Tidak* |
| `AZURE_OPENAI_KEY` | Azure OpenAI API key | Tidak* |
| `AZURE_OPENAI_DEPLOYMENT` | Nama deployment (default: `gpt-4o`) | Tidak* |
| `PROVINCE_CONFIG_PATH` | Path ke `province_master_config.json` | Tidak** |
| `MODEL_ELIGIBILITY_PATH` | Path ke `.pkl` eligibility | Tidak** |
| `MODEL_ANOMALY_PATH` | Path ke `.pkl` anomaly | Tidak** |

\* Jika tidak diset, policy brief menggunakan template fallback (tidak error).  
\*\* **Jangan diset saat development lokal** — `config.py` resolve otomatis relatif terhadap root repo (cross-platform).

---

## Menjalankan (Local Dev)

```bash
# Pastikan sudah ada file model di model/output/
# Jika belum, jalankan dulu: python model/rerun_pipeline.py

cd backend
python -m uvicorn main:app --reload --port 8000
```

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## Docker

Dockerfile dibangun dari **root repo** (bukan dari dalam `backend/`):

```bash
# Build
docker build -f backend/Dockerfile -t rightaid-api .

# Run
docker run -p 8000:8000 \
  -e SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')" \
  -e RIGHTAID_USERS_JSON='[{"email":"guest@rightaid.id","password":"guest123","name":"Guest","role":"guest"}]' \
  rightaid-api
```

---

## Province ID

Backend menerima province ID dalam dua format:
- **Kode pendek**: `"JB"`, `"JK"`, `"JT"`, `"JI"`, `"AC"`, dll.
- **Nama lengkap**: `"Jawa Barat"`, `"DKI Jakarta"`, dll.

Lihat mapping lengkap di [`services/data_generator.py`](services/data_generator.py) → `PROVINCE_CODE`.

---

## Upload Data

Endpoint `POST /api/upload` menerima file CSV atau JSON dengan kolom sesuai template:

```bash
# Download template
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/api/upload/template -o template.csv

# Upload
curl -X POST http://localhost:8000/api/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@data.csv" \
  -F "province_id=JB" \
  -F "scenario=normal"
```

Kolom wajib ada di data yang diupload: lihat `REQUIRED_COLUMNS` di [`services/data_loader.py`](services/data_loader.py).
