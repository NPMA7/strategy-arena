# Spesifikasi Strategi #31: Multi-Horizon Momentum (`momentum_60`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **Multi-Horizon Momentum**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#31` · `momentum_60` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Momentum** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (1-Menit Bar Closed via `BarRing`) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 2.0`** | Otomatis berdasarkan cluster `Momentum` |
| **Leverage Default** | **`12x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.35\% \times \text{Harga})$ | Floor proteksi minimum 0.35% di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Mengukur akselerasi momentum berjenjang pada 3 jendela 20-bar berurutan (0..20, 20..40, 40..60 bar).

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. $r_1 = \frac{C_i}{C_{i-20}} - 1, \; r_2 = \frac{C_{i-20}}{C_{i-40}} - 1, \; r_3 = \frac{C_{i-40}}{C_{i-60}} - 1$
2. **BUY**: $r_1, r_2, r_3 > 0$ dan $r_1 > r_2$ (akselerasi naik)
3. **SELL**: $r_1, r_2, r_3 < 0$ dan $r_1 < r_2$ (akselerasi turun)

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  r3 (+1%) ---> r2 (+1.5%) ---> r1 (+2.2%) ===> Akselerasi Penuh -> ENTRY
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

* **⚠️ Masuk di Fase Akhir Parabolik**: Setelah harga naik selama 60 bar berturut-turut dan berakselerasi (`r1 > r2`), kondisi harga umumnya sudah jenuh beli (*overextended*), menyebabkan posisi sering masuk di ujung pucuk (`-2.75%`).
* **⚠️ Catatan Umum Mesin M1 (`0.35% Minimum SL Floor`)**: Karena sinyal dievaluasi pada bar **1-menit (`M1`)**, sedangkan `engine.py` memaksa jarak Stop Loss minimal `0.35%` (~143 pips pada XAUUSD atau ~39 pips pada EURUSD), strategi jangka pendek M1 harus menahan fluktuasi lebar yang kerap tidak sebanding dengan target scalping-nya.

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'momentum_60':
def momentum_weeks(s):
    """Momentum 60 candle bertingkat (gaya time-series momentum)."""
    i = s.i
    if i < 60:
        return 0.0
    r1 = s.c[i] / s.c[i - 20] - 1
    r2 = s.c[i - 20] / s.c[i - 40] - 1
    r3 = s.c[i - 40] / s.c[i - 60] - 1
    if r1 > 0 and r2 > 0 and r3 > 0 and r1 > r2:
        return 0.75
    if r1 < 0 and r2 < 0 and r3 < 0 and r1 < r2:
        return -0.75
    return 0.0
```
