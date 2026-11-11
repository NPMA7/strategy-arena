# Spesifikasi Strategi #2: ICT Fair Value Gap (`ict_fvg`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **ICT Fair Value Gap**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#2` · `ict_fvg` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **ICT** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (1-Menit Bar Closed via `BarRing`) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.8`** | Otomatis berdasarkan cluster `ICT` |
| **Leverage Default** | **`12x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.35\% \times \text{Harga})$ | Floor proteksi minimum 0.35% di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Mendeteksi Fair Value Gap (ketidakseimbangan harga 3 candle antara High candle pertama dan Low candle ketiga), lalu entry saat harga masuk kembali ke tengah area gap untuk mitigasi.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. **Bullish FVG**: $L_{i-2} > H_{i-4}$
2. **Bearish FVG**: $H_{i-2} < L_{i-4}$
3. $\text{GapMid} = \frac{L_{i-2} + H_{i-4}}{2}$ (atau kebalikannya untuk Bearish)
4. **Trigger**: $\frac{|C_i - \text{GapMid}|}{C_i} < 0.004$

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  Bar [i-4]  +---+ High
             |   |          <--- Celah Imbalance (FVG Zone)
  Bar [i-2]  |   +---+ Low  <--- Retest ke Tengah Celah (|C - Mid|/C < 0.4%)
             +-------+
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
   - $\text{TPDist} = 1.8 \times \text{StopDist}$
   - Jika muncul sinyal berlawanan arah (`pos.side != new_side`), posisi lama langsung ditutup (*reverse signal exit*) sebelum posisi baru dibuka.

---

## 5. Audit Risiko, Temuan Bug & Titik Lemah (*CRITICAL AUDIT*)

Hasil pemeriksaan langsung terhadap kode sumber `server/strategies.py`, `server/engine.py`, dan `server/forex_feed.py` menemukan catatan audit spesifik berikut untuk strategi ini:

* **⚠️ Indeks Statis Tanpa Memori FVG**: Hanya melihat FVG yang terbentuk tepat pada `i-4` ke `i-2` (berusia 2 candle). Jika mitigasi terjadi 5-15 candle kemudian, gap sudah dilupakan oleh algoritma.
* **⚠️ Skala Ambang `0.004` (0.4%) Tidak Universal**: Di pasar Forex (contoh EURUSD 1.1000), jarak `0.4%` setara ±44 pips, sehingga kondisi terpenuhi bahkan saat harga berada jauh di luar gap M1 yang cuma 2-3 pips.
* **⚠️ Catatan Umum Mesin M1 (`0.35% Minimum SL Floor`)**: Karena sinyal dievaluasi pada bar **1-menit (`M1`)**, sedangkan `engine.py` memaksa jarak Stop Loss minimal `0.35%` (~143 pips pada XAUUSD atau ~39 pips pada EURUSD), strategi jangka pendek M1 harus menahan fluktuasi lebar yang kerap tidak sebanding dengan target scalping-nya.

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'ict_fvg':
def fvg_ict(s):
    """Fair Value Gap: gap antara high bar-2 dan low bar-0 lalu diisi (retest)."""
    i = s.i
    if i < 3:
        return 0.0
    gap_up = s.l[i - 2] > s.h[i - 4]
    gap_dn = s.h[i - 2] < s.l[i - 4]
    if not (gap_up or gap_dn):
        return 0.0
    c = s.c[i]
    if gap_up and abs(c - (s.l[i - 2] + s.h[i - 4]) / 2) / c < 0.004:
        return 0.65
    if gap_dn and abs(c - (s.h[i - 2] + s.l[i - 4]) / 2) / c < 0.004:
        return -0.65
    return 0.0
```
