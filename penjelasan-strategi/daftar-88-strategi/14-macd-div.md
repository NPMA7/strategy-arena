# Spesifikasi Strategi #14: MACD Divergence (`macd_div`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **MACD Divergence**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#14` · `macd_div` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Momentum** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (1-Menit Bar Closed via `BarRing`) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 2.0`** | Otomatis berdasarkan cluster `Momentum` |
| **Leverage Default** | **`12x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.35\% \times \text{Harga})$ | Floor proteksi minimum 0.35% di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Mencari divergensi antara harga dan MACD: harga mencetak Lower Low tapi MACD mencetak Higher Low (Bullish Divergence) dengan pemicu harga close di atas EMA9.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. Membandingkan min/max window `[i-25:i-5]` vs `[i-20:i+1]` pada Harga dan MACD.
2. **BUY**: $\text{Low}_{now} < \text{Low}_{prev}$ dan $\text{MACD}_{low,now} > \text{MACD}_{low,prev}$ dan $C_i > \text{EMA}_9$

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  Harga:  \___      / (Lower Low)
              \____/
  MACD :  \____/      (Higher Low) ===> BULLISH DIVERGENCE
```

---

## 4. Logika Eksekusi & Proteksi Risiko di Arena Engine

Setiap kali bar M1 (`BarRing`) menutup dan indikator `Snap` selesai dihitung:
1. **Validasi Posisi & Batas Risiko**:
   - Maksimal **5 posisi terbuka simultan** antar pair (`MAX_POS = 5`).
   - Jika slot penuh tetapi muncul sinyal baru dengan `abs(score)` lebih kuat, engine dapat menjalankan `risk_rotasi` (menutup posisi terlemah untuk digantikan sinyal baru).
   - Apabila strategi mencapai batas **3x Margin Call (MC)**, akun dinonaktifkan permanen (`OFF 3x MC`) dan tidak membuka posisi baru lagi.
2. **Penentuan Ukuran Lot & Margin**:
   - **Mode Forex MT5**: Risiko ditargetkan `1.5%` dari cash per posisi (`~$15` pada modal `$1,000`), dibatasi `0.01 - 0.10 Lot` (XAU/XTI) atau `0.01 - 0.20 Lot` (Forex mayor/cross).
   - **Mode Futures/Spot**: Risiko ditargetkan `2.0%` equity dengan margin maksimum per posisi `20%` equity (`SINGLE_POS_CAP`).
3. **Stop Loss & Take Profit**:
   - $\text{StopDist} = \max(2.0 \times \text{ATR}_{14}(M1), \; 0.0035 \times \text{Price})$
   - $\text{TPDist} = 2.0 \times \text{StopDist}$
   - Jika muncul sinyal berlawanan arah (`pos.side != new_side`), posisi lama langsung ditutup (*reverse signal exit*) sebelum posisi baru dibuka.

---

## 5. Audit Risiko, Temuan Bug & Titik Lemah (*CRITICAL AUDIT*)

Hasil pemeriksaan langsung terhadap kode sumber `server/strategies.py`, `server/engine.py`, dan `server/forex_feed.py` menemukan catatan audit spesifik berikut untuk strategi ini:

* **🚨 CRITICAL BUG (Overlapping Slice Windows!)**: Window pembanding pertama `[i-25:i-5]` dan kedua `[i-20:i+1]` **BERTUMPUKAN (OVERLAP) SEBANYAK 15 BAR** (`i-20` s/d `i-5`)! Akibatnya jika nilai terendah berada di zona overlap, kedua variabel membaca bar yang persis sama. Selain itu fungsi ini tidak memverifikasi apakah puncak harga dan puncak MACD terjadi pada waktu yang sama.
* **⚠️ Catatan Umum Mesin M1 (`0.35% Minimum SL Floor`)**: Karena sinyal dievaluasi pada bar **1-menit (`M1`)**, sedangkan `engine.py` memaksa jarak Stop Loss minimal `0.35%` (~143 pips pada XAUUSD atau ~39 pips pada EURUSD), strategi jangka pendek M1 harus menahan fluktuasi lebar yang kerap tidak sebanding dengan target scalping-nya.

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'macd_div':
def macd_divergence(s):
    i = s.i
    if i < 25:
        return 0.0
    px_low_prev = float(s.l[i - 25:i - 5].min())
    px_low_now = float(s.l[i - 20:i + 1].min())
    macd_low_prev = float(s.macd[i - 25:i - 5].min())
    macd_low_now = float(s.macd[i - 20:i + 1].min())
    px_hi_prev = float(s.h[i - 25:i - 5].max())
    px_hi_now = float(s.h[i - 20:i + 1].max())
    macd_hi_prev = float(s.macd[i - 25:i - 5].max())
    macd_hi_now = float(s.macd[i - 20:i + 1].max())
    if px_low_now < px_low_prev and macd_low_now > macd_low_prev and s.c[i] > s.ema9[i]:
        return 0.65
    if px_hi_now > px_hi_prev and macd_hi_now < macd_hi_prev and s.c[i] < s.ema9[i]:
        return -0.65
    return 0.0
```
