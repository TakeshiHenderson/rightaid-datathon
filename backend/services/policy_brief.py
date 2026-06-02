"""Generates a 2-page policy brief in Bahasa Indonesia via Azure OpenAI.
Falls back to a template-based brief if Azure OpenAI is not configured.
"""
from config import settings

SCENARIO_LABELS = {
    "normal": "Kondisi Normal (Baseline)",
    "phk": "PHK Massal (Sektor Manufaktur)",
    "bencana": "Pasca-Bencana",
}

_FALLBACK_TEMPLATE = """**1. RINGKASAN TEMUAN UTAMA**

Berdasarkan analisis sistem RightAid ML-PMT terhadap {total_records:,} rumah tangga di **{province}** dalam skenario **{scenario_label}**:

- Model ML mencatat **exclusion error {ml_exclusion_err:.1f}%** vs PMT konvensional **{pmt_exclusion_err:.1f}%** — pengurangan {pmt_excl_diff:.1f} poin persentase.
- Inclusion error model ML **{ml_inclusion_err:.1f}%** vs PMT **{pmt_inclusion_err:.1f}%**.
- F1-score model ML: **{ml_f1:.4f}** vs PMT: **{pmt_f1:.4f}** (AUC-ROC: {ml_auc:.4f}).
- Persentase kasus anomali/mis-targeting terdeteksi: **{anomaly_pct:.1f}%** dari total sampel.

Model ML secara konsisten mengungguli PMT konvensional dalam mendeteksi rumah tangga yang layak menerima bantuan sosial, terutama pada kelompok yang kondisinya berubah akibat skenario {scenario_label}.

---

**2. PROFIL DEMOGRAFIS TERDAMPAK**

Kelompok paling rentan terhadap exclusion error dalam skenario {scenario_label} di {province} umumnya memiliki karakteristik:

- Kepala rumah tangga berusia 35–55 tahun dengan pendidikan SMP–SMA
- Bekerja di sektor informal atau terdampak langsung oleh skenario (PHK/bencana)
- Memiliki aset fisik (kendaraan, elektronik) dari periode sebelum kondisi berubah, sehingga skor PMT konvensional masih tinggi meski kondisi ekonomi aktual sudah menurun
- Tinggal di wilayah peri-urban dengan akses layanan sosial yang terbatas

Inkonsistensi ini menjadi "blind spot" PMT konvensional karena sistem tidak memperbarui data secara real-time.

---

**3. REKOMENDASI TINDAK LANJUT**

1. **Verifikasi lapangan prioritas**: Tindak lanjuti {estimated_fn:,} rumah tangga yang diprediksi model ML sebagai layak bansos namun belum tercatat dalam DTSEN. Prioritaskan berdasarkan skor probabilitas ML tertinggi.

2. **Integrasi data lintas sektor**: Koordinasikan dengan BPJS Ketenagakerjaan (data PHK), BNPB (data bencana), dan Dukcapil (data perubahan komposisi keluarga) sebagai pemicu pembaruan data otomatis.

3. **Pembaruan formula PMT**: Tinjau ulang bobot variabel aset statis (kendaraan, bangunan) yang tidak mencerminkan perubahan kondisi ekonomi dinamis. Pertimbangkan penambahan variabel pengeluaran aktual sebagai indikator silang.

4. **Implementasi sistem monitoring**: Terapkan dashboard ML-PMT secara berkala (minimal triwulan) untuk mendeteksi pergeseran profil kerentanan sebelum data DTSEN diperbarui secara formal.

---
*Laporan ini dihasilkan oleh sistem RightAid ML-PMT Refresher berdasarkan data simulasi berbasis distribusi BPS Susenas.*
"""


def _build_fallback(province: str, scenario: str, stats: dict) -> dict:
    scenario_label = SCENARIO_LABELS.get(scenario, scenario)
    total = stats.get("total_records", 10000)
    eligible_pct = stats.get("eligible_pct", 40)
    estimated_fn = int(total * stats.get("ml_exclusion_err", 5) / 100)

    content = _FALLBACK_TEMPLATE.format(
        province=province,
        scenario_label=scenario_label,
        total_records=total,
        eligible_pct=eligible_pct,
        pmt_exclusion_err=stats.get("pmt_exclusion_err", 0),
        ml_exclusion_err=stats.get("ml_exclusion_err", 0),
        pmt_excl_diff=round(stats.get("pmt_exclusion_err", 0) - stats.get("ml_exclusion_err", 0), 1),
        pmt_inclusion_err=stats.get("pmt_inclusion_err", 0),
        ml_inclusion_err=stats.get("ml_inclusion_err", 0),
        anomaly_pct=stats.get("anomaly_pct", 0) * 100,
        ml_f1=stats.get("ml_f1", 0),
        pmt_f1=stats.get("pmt_f1", 0),
        ml_auc=stats.get("ml_auc", 0),
        estimated_fn=estimated_fn,
    )
    title = f"Policy Brief: Analisis Mis-Targeting Bansos — {province} ({scenario_label})"
    return {"title": title, "content": content}


def generate(province: str, scenario: str, stats: dict) -> dict:
    """
    stats keys expected:
      total_records, eligible_pct, pmt_exclusion_err, ml_exclusion_err,
      pmt_inclusion_err, ml_inclusion_err, anomaly_pct,
      ml_f1, ml_auc, pmt_f1
    """
    # Use Azure OpenAI only if fully configured
    if not settings.AZURE_OPENAI_ENDPOINT or not settings.AZURE_OPENAI_KEY:
        return _build_fallback(province, scenario, stats)

    try:
        from openai import AzureOpenAI
        client = AzureOpenAI(
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_KEY,
            api_version="2024-02-01",
        )
        scenario_label = SCENARIO_LABELS.get(scenario, scenario)
        prompt = f"""Anda adalah analis kebijakan sosial senior di Indonesia.
Buatkan policy brief dua halaman dalam Bahasa Indonesia yang profesional berdasarkan
hasil simulasi sistem RightAid ML-PMT Refresher untuk {province} dalam skenario {scenario_label}.

Data hasil simulasi:
- Total rumah tangga dianalisis: {stats.get('total_records', 10000):,}
- Persentase rumah tangga layak bansos (desil ≤ 4): {stats.get('eligible_pct', 40):.1f}%
- Exclusion error PMT konvensional (yang layak tapi terlewat): {stats.get('pmt_exclusion_err', 0):.2f}%
- Exclusion error model ML: {stats.get('ml_exclusion_err', 0):.2f}%
- Inclusion error PMT konvensional: {stats.get('pmt_inclusion_err', 0):.2f}%
- Inclusion error model ML: {stats.get('ml_inclusion_err', 0):.2f}%
- Persentase anomali/kasus mis-targeting terdeteksi: {stats.get('anomaly_pct', 0)*100:.1f}%
- F1-score model ML: {stats.get('ml_f1', 0):.4f} vs PMT: {stats.get('pmt_f1', 0):.4f}
- AUC model ML: {stats.get('ml_auc', 0):.4f}

Susun policy brief dengan struktur berikut (gunakan heading yang jelas):

1. RINGKASAN TEMUAN UTAMA
   Deskripsikan tingkat mis-targeting PMT konvensional vs model ML untuk {province}
   dalam skenario {scenario_label}. Sebutkan angka konkret.

2. PROFIL DEMOGRAFIS TERDAMPAK
   Jelaskan karakteristik kelompok yang paling sering terlewat (excluded) oleh PMT
   berdasarkan skenario ini (pekerja formal yang di-PHK / korban bencana / dll).

3. REKOMENDASI TINDAK LANJUT
   Berikan 3-4 rekomendasi kebijakan yang dapat segera ditindaklanjuti oleh
   Kemensos/Dinsos dalam 6 bulan ke depan.

Gunakan bahasa yang dapat dipahami oleh pejabat non-teknis. Maksimal 600 kata."""

        response = client.chat.completions.create(
            model=settings.AZURE_OPENAI_DEPLOYMENT,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.4,
        )
        content = response.choices[0].message.content
        title = f"Policy Brief: Analisis Mis-Targeting Bansos — {province} ({scenario_label})"
        return {"title": title, "content": content}

    except Exception:
        # Fallback if Azure OpenAI call fails for any reason
        return _build_fallback(province, scenario, stats)
