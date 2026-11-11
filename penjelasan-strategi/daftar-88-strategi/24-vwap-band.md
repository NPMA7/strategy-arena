# Spesifikasi Strategi #24: VWAP Deviation (`vwap_band`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **VWAP Deviation**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#24` · `vwap_band` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Statistik** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (1-Menit Bar Closed via `BarRing`) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.5`** | Otomatis berdasarkan cluster `Statistik` |
| **Leverage Default** | **`12x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.35\% \times \text{Harga})$ | Floor proteksi minimum 0.35% di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Mean reversion statistik menggunakan VWAP 60-bar dan standar deviasi terbobot volume: membeli saat Z-Score < -2 dan menjual saat Z-Score > +2.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. $\text{VWAP} = \frac{\sum C_k V_k}{\sum V_k}$, $\quad \sigma = \sqrt{\frac{\sum (C_k - \text{VWAP})^2 V_k}{\sum V_k}}$
2. $Z = \frac{C_i - \text{VWAP}}{\sigma}$
3. **BUY** jika $Z < -2.0$, **SELL** jika $Z > +2.0$

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  +2 SD  ---/\--- (SELL: Z > 2)
  VWAP   -------- (Mean Magnet)
  -2 SD  ---\/--- (BUY: Z < -2)
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
   - $\text{TPDist} = 1.5 \times \text{StopDist}$
   - Jika muncul sinyal berlawanan arah (`pos.side != new_side`), posisi lama langsung ditutup (*reverse signal exit*) sebelum posisi baru dibuka.

---

## 5. Audit Risiko, Temuan Bug & Titik Lemah (*CRITICAL AUDIT*)

Hasil pemeriksaan langsung terhadap kode sumber `server/strategies.py`, `server/engine.py`, dan `server/forex_feed.py` menemukan catatan audit spesifik berikut untuk strategi ini:

* **⚠️ Catatan Data Volume Forex**: Di `forex_feed.py`, volume bar Forex dibuat dengan `random.uniform(0.1, 5.0)` per tick, sehingga bobot volume di pasar Forex bersifat acak (meski karena banyaknya tick/menit nilainya merata mendekati SMA terbobot merata).
* **⚠️ Tidak Memeriksa Pembalikan**: Entry dilakukan segera selama $Z > 2$ atau $Z < -2$ tanpa menunggu harga berhenti melaju.
* **⚠️ Catatan Umum Mesin M1 (`0.35% Minimum SL Floor`)**: Karena sinyal dievaluasi pada bar **1-menit (`M1`)**, sedangkan `engine.py` memaksa jarak Stop Loss minimal `0.35%` (~143 pips pada XAUUSD atau ~39 pips pada EURUSD), strategi jangka pendek M1 harus menahan fluktuasi lebar yang kerap tidak sebanding dengan target scalping-nya.

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'vwap_band':
def vwap_band(s):
    """VWAP jendela 60 candle, mean reversion ke band."""
    i = s.i
    a, b = max(0, i - 59), i + 1
    vv = s.v[a:b]
    tot = float(vv.sum())
    if tot <= 0:
        return 0.0
    vwap = float((s.c[a:b] * vv).sum() / tot)
    sd = float((((s.c[a:b] - vwap) ** 2) * vv).sum() / tot) ** 0.5
    if sd <= 0:
        return 0.0
    z = (s.c[i] - vwap) / sd
    if z < -2:
        return min(0.9, abs(z) / 3)
    if z > 2:
        return -min(0.9, abs(z) / 3)
    return 0.0
```
