# frontend/ — RightAid Web Dashboard

> Static web app (HTML + CSS + JS murni, tanpa build step).
> Untuk setup lengkap termasuk backend, lihat [README utama](../README.md).

---

## Cara Menjalankan

Frontend tidak memerlukan build step apapun. Cukup serve direktori ini:

```bash
# Cara 1 — Python (paling mudah)
cd frontend
python -m http.server 5500

# Cara 2 — Node.js
cd frontend
npx serve .

# Cara 3 — VS Code: klik kanan index.html → "Open with Live Server"
```

Buka browser: `http://localhost:5500`

**Login default:**
- Email: `guest@rightaid.id`
- Password: `guest123`

---

## Koneksi ke Backend

Frontend otomatis mendeteksi environment:

| URL yang diakses | Backend URL yang digunakan |
|---|---|
| `localhost` / `127.0.0.1` / IP lokal | `http://localhost:8000` |
| Domain produksi (Azure) | `https://rightaid-api.azurewebsites.net` (atau `window.RIGHTAID_API_URL`) |

Untuk development lokal, pastikan backend sudah berjalan di port 8000 sebelum membuka frontend.

> **Offline mode:** Jika backend tidak tersedia, semua halaman otomatis jatuh ke data dummy (`js/data.js`). Ini memungkinkan frontend tetap bisa di-demo tanpa backend.

---

## Struktur File

```
frontend/
├── index.html          # Login page
├── dashboard.html      # Beranda — statistik nasional
├── analysis.html       # Analisis targeting + SHAP + upload data
├── data-viewer.html    # Tabel data rumah tangga per provinsi
├── policy.html         # Generator policy brief
├── favicon.svg
├── staticwebapp.config.json   # Config Azure Static Web Apps
├── css/
│   └── style.css       # Design system (dark theme, glassmorphism)
└── js/
    ├── app.js          # Shared utilities + FULL API layer
    └── data.js         # Dummy/fallback data (EkoData)
```

---

## API Layer (`js/app.js`)

Semua pemanggilan backend terpusat di `window.App.*`:

```js
App.loginAPI(email, password)          // POST /api/auth/login
App.fetchNationalStats()               // GET  /api/stats/national
App.fetchProvinces()                   // GET  /api/provinces
App.apiGenerate(pid, scenario, pct, n) // POST /api/generate
App.apiUpload(file, pid, scenario)     // POST /api/upload
App.apiPredict(sessionId)              // POST /api/predict/{id}
App.fetchSHAP(sessionId, recordId)     // GET  /api/shap/{id}/{rid}
App.apiPolicyBrief(sid, pid, scenario) // POST /api/policy-brief
App.exportDataCSV(sessionId)           // GET  /api/data/{id}/export
```

---

## Teknologi

- **HTML5 + Vanilla CSS + Vanilla JS** — tanpa framework, tanpa build step
- **Design system**: dark mode, glassmorphism, CSS variables, micro-animations
- **Charts**: canvas-based (`App.drawBarChart`, `App.drawLineChart`)
- **SHAP visualization**: custom horizontal bar renderer (`App.renderSHAP`)
- **Font**: Inter (Google Fonts)
