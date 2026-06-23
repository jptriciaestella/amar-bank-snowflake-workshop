# Session 2 — Data Analytics & Build Streamlit pakai AI (Detail untuk Pemula)

🎯 **Tujuan besar session ini:**
1. Menjalankan analitik di Snowflake & memahami **performa warehouse** dan **cache**.
2. **Membangun dashboard Streamlit hanya dengan mengetik perintah ke AI** (tanpa coding manual).

> Prasyarat: Jalankan `sql/05_prereq_day2.sql` (atau Session 1 selesai) → tabel `GOLD.MART_LOAN_PERFORMANCE` & `GOLD.MART_CUSTOMER_360` sudah ada.

---

# BAGIAN A — Analitik & Performa (SQL)

Buka worksheet baru, set konteks: Role apa saja, Warehouse `AMAR_WORKSHOP_WH`,
Database `AMAR_WORKSHOP`, Schema `GOLD`. Referensi perintah: `sql/04_analytics.sql`.

## A.1 Query bisnis pertama

🎯 **Tujuan:** menjawab pertanyaan bisnis nyata: "Berapa NPL (kredit macet) per produk?"

👉 **Langkah:** jalankan:
```sql
SELECT product_segment,
       COUNT(*) AS n_loans,
       SUM(is_default) AS n_default,
       ROUND(100 * SUM(is_default)/COUNT(*), 2) AS npl_rate_pct,
       SUM(outstanding) AS total_outstanding
FROM GOLD.MART_LOAN_PERFORMANCE
GROUP BY product_segment
ORDER BY npl_rate_pct DESC;
```

👀 **Yang harus dilihat:** tabel berisi `Tunaiku` & `SMB` dengan kolom `npl_rate_pct`.
**Artinya:** dalam hitungan detik, Anda dapat metrik risiko portofolio dari jutaan baris.

## A.2 Performa Warehouse — Scale Up

🎯 **Tujuan:** membuktikan menambah ukuran "mesin" mempercepat query berat.

👉 **Langkah:**
1. Matikan cache agar adil:
   ```sql
   ALTER SESSION SET USE_CACHED_RESULT = FALSE;
   ALTER WAREHOUSE AMAR_WORKSHOP_WH SET WAREHOUSE_SIZE = 'XSMALL';
   ```
2. Jalankan query berat (join + agregasi) — lihat di `sql/04_analytics.sql` bagian A.2.
3. Catat durasinya (lihat panel **Query Details / Duration**).
4. Perbesar mesin lalu jalankan query **yang sama**:
   ```sql
   ALTER WAREHOUSE AMAR_WORKSHOP_WH SET WAREHOUSE_SIZE = 'LARGE';
   ```

👀 **Yang harus dilihat:** durasi query **turun signifikan** di warehouse LARGE.
**Artinya:** di Snowflake, menambah tenaga komputasi cukup 1 perintah (atau 1 klik),
tanpa migrasi server. Jangan lupa kecilkan lagi:
```sql
ALTER WAREHOUSE AMAR_WORKSHOP_WH SET WAREHOUSE_SIZE = 'SMALL';
```

> 📌 **Scale UP vs Scale OUT:** *up* = mesin lebih besar (query berat). *out* = banyak
> mesin paralel/multi-cluster (banyak user bersamaan).

## A.3 Result Cache

🎯 **Tujuan:** melihat query yang sama jadi instan & **gratis** (tanpa compute).

👉 **Langkah:**
```sql
ALTER SESSION SET USE_CACHED_RESULT = TRUE;
SELECT product_segment, COUNT(*) FROM GOLD.MART_LOAN_PERFORMANCE GROUP BY 1;  -- run #1
SELECT product_segment, COUNT(*) FROM GOLD.MART_LOAN_PERFORMANCE GROUP BY 1;  -- run #2
```

👀 **Yang harus dilihat:** run #2 selesai **hampir 0 detik**. Cek di **Query History**:
kolom *Bytes scanned* = 0 / dilayani dari cache. **Artinya:** hemat biaya untuk query berulang.

---

# BAGIAN B — Membangun Streamlit dengan AI (tanpa coding!)

🎯 **Tujuan:** Menunjukkan bahwa siapa pun (bahkan non-programmer) bisa membuat dashboard
interaktif **hanya dengan mengetik permintaan ke AI** di dalam Snowflake.

> **Konsep:** Streamlit = framework untuk membuat aplikasi data interaktif dengan Python.
> Di Snowsight ada editor Streamlit dengan **asisten AI (Cortex)** — kita cukup memberi
> instruksi bahasa natural, AI menuliskan kodenya.

## B.1 Membuat App Streamlit kosong

👉 **Langkah:**
1. Snowsight → menu kiri **Projects → Streamlit**.
2. Klik **+ Streamlit App** (kanan atas).
3. Isi: **App title** = `Amar Loan Dashboard`, **Warehouse** = `AMAR_WORKSHOP_WH`,
   **Database/Schema** = `AMAR_WORKSHOP` / `GOLD`. Klik **Create**.
4. Akan terbuka editor: kiri = kode, kanan = preview app.

👀 **Yang harus dilihat:** sebuah app contoh tampil di sebelah kanan.

## B.2 Membuka asisten AI

👉 **Langkah:** di dalam editor Streamlit, cari tombol/panel **AI** (ikon Cortex /
"Ask Copilot" — biasanya di toolbar editor atau klik kanan). Buka panel chat AI.

> Jika fitur AI assistant belum aktif di akun, Anda tetap bisa **paste** kode jadi dari
> file `streamlit/streamlit_app.py` (solusi referensi) — tapi tujuan demo ini adalah
> memakai AI.

## B.3 Prompt siap copy-paste

Ketik/paste prompt berikut **satu per satu** ke asisten AI. Setelah tiap prompt, klik
**Run** untuk melihat hasilnya di preview. Tujuannya: membuat dashboard **profesional
berkualitas Looker** — bukan demo sederhana.

### Prompt 1 — Kerangka, koneksi data & styling profesional
```
Buatkan aplikasi Streamlit-in-Snowflake dashboard portofolio pinjaman Amar Bank.
Gunakan get_active_session() dari snowflake.snowpark.context untuk koneksi.
Ambil data dari dua tabel:
- AMAR_WORKSHOP.GOLD.MART_LOAN_PERFORMANCE
- AMAR_WORKSHOP.GOLD.MART_CUSTOMER_360

Styling:
- layout="wide", page_title="Amar Bank — Portfolio Intelligence", page_icon="🏦"
- Tambahkan custom CSS: sidebar dengan gradient gelap (dark navy #1a1a2e ke #0f3460),
  dan card KPI dengan gradient background (ungu-biru #667eea ke #764ba2, putih teks,
  rounded corners, box-shadow). Buat class .metric-card, .metric-card-green, .metric-card-orange.
- Gunakan @st.cache_data(ttl=600) untuk fungsi query.
```

### Prompt 2 — Sidebar filter & 5 KPI cards
```
Tambahkan sidebar dengan:
- Logo placeholder (atau teks "🏦 Amar Bank")
- 3 selectbox filter: Product Segment, Province, DPD Bucket (masing-masing ada opsi "All")
- Caption "Data sintetis untuk workshop"

Di body utama, tampilkan 5 KPI cards (pakai st.markdown + HTML div class metric-card):
1. Total Loans (format ribuan)
2. NPL Rate (rata-rata IS_DEFAULT * 100, format persen, card oranye)
3. Total Outstanding (format "Rp X.XB", card hijau)
4. Total Customers (card biru)
5. Avg Collection Rate (rata-rata COLLECTION_RATIO * 100, card hijau)

Semua KPI harus responsive terhadap filter sidebar.
```

### Prompt 3 — Tab Portfolio Overview (bar + donut + tabel)
```
Buat 4 tabs: "📊 Portfolio Overview", "⚠️ Risk & DPD Analysis", "👥 Customer 360", "📈 Trend & Collection".

Di tab Portfolio Overview:
- Layout 2 kolom (3:2 ratio)
- Kiri: bar chart Outstanding per PRODUCT_SEGMENT, pakai Altair mark_bar dengan cornerRadius,
  warna gradient palette ["#667eea", "#764ba2", "#f5576c", "#4facfe", "#38ef7d"].
  Tooltip: segment, jumlah loan, outstanding, NPL rate.
- Kanan: donut chart (mark_arc innerRadius=55) komposisi jumlah pinjaman per segment.
- Bawah: dataframe tabel ringkasan per segment (loans, outstanding billions, NPL %, avg plafond).
```

### Prompt 4 — Tab Risk & DPD Analysis (bar + donut + heatmap)
```
Di tab Risk & DPD Analysis:
- 2 kolom: kiri bar chart jumlah pinjaman per DPD_BUCKET (urut: CURRENT, DPD_1_30, DPD_31_60,
  DPD_61_90, DPD_90_PLUS), warna hijau→kuning→oranye→merah (gradient risiko).
- Kanan: donut chart outstanding per DPD_BUCKET.
- Bawah: heatmap (mark_rect) Product Segment vs DPD Bucket, warna intensitas = jumlah loans
  (color scheme "blues").
```

### Prompt 5 — Tab Customer 360 (horizontal bar + pie + histogram)
```
Di tab Customer 360:
- 2 kolom (3:2). Kiri: horizontal bar chart top 15 provinces by customer count,
  urut descending, warna scheme "purples".
- Kanan atas: donut chart segmen nasabah (Tunaiku/Senyumku/SMB).
- Kanan bawah: histogram credit_score (bin=20), warna ungu semi-transparan.
```

### Prompt 6 — Tab Trend & Collection + footer
```
Di tab Trend & Collection:
- Kiri: bar chart Avg Collection Ratio % per Product Segment, tambahkan garis merah putus-putus
  di y=100% sebagai target line (alt.Chart rule).
- Kanan: area chart disbursement volume (Miliar Rp) per bulan dari kolom DISBURSED_AT
  (extract month), pakai gradient fill transparan.
- Bawah: st.metric per segment untuk rata-rata late payments & max days late.

Tambahkan footer di paling bawah: centered, warna abu, teks
"🏦 Amar Bank Portfolio Intelligence · Built with Streamlit-in-Snowflake · Data: Synthetic"
```

👀 **Yang harus dilihat di tiap langkah:**
- Setelah Prompt 1–2: sidebar gelap + 5 KPI cards berwarna (gradient) + filter interaktif.
- Setelah Prompt 3–4: 4 tab profesional — bar chart dengan rounded corners, donut chart,
  heatmap, tooltip kaya informasi.
- Setelah Prompt 5–6: area chart, histogram, late-payment metrics, footer.
- Semua chart merespons filter sidebar — **interaktif seperti Looker/Tableau**.

> 💡 **Pesan untuk audiens:** Dashboard ini dibangun 100% lewat prompt AI, berjalan
> di dalam Snowflake (data tidak keluar), dan hasilnya setara BI tools komersial.

## B.4 Menyimpan & membagikan

👉 **Langkah:** klik **Save**. Bagikan app ke role lain via tombol **Share** (mis. ke
`AMAR_ANALYST`).

👀 **Yang harus dilihat:** app tersimpan & bisa dibuka ulang dari Projects → Streamlit.

> 💡 **Pesan kunci ke customer:** "Dari nol sampai dashboard interaktif berkualitas Looker
> **tanpa menulis kode manual** — cukup memberi instruksi ke AI, dan semuanya berjalan
> **di dalam** Snowflake (data tidak keluar). Hasilnya bisa langsung di-share ke tim."

---

## Ringkasan Session 2
- ✅ Bisa menjawab pertanyaan bisnis dengan SQL di Snowflake.
- ✅ Paham scale up/out & result cache (kcontrol biaya + performa).
- ✅ Membangun dashboard Streamlit **menggunakan AI** lewat prompt copy-paste.

📎 **Solusi referensi** (jika AI assistant tidak tersedia): `streamlit/streamlit_app.py`.

➡️ Lanjut ke **[Session 3 — Data Governance](GUIDE_SESSION3_GOVERNANCE.md)**.
