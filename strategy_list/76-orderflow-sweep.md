# Spesifikasi Strategi #76: Order Flow Liquidity Sweep (`orderflow_sweep`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **Order Flow Liquidity Sweep**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#76` · `orderflow_sweep` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Order flow** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (`BarRing` kapasitas 1440 bar / 24 jam) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 2.0`** | Otomatis berdasarkan cluster `Order flow` |
| **Leverage Default** | **`15x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.10\% \text{ Forex} / 0.35\% \text{ Crypto})$ | Floor proteksi adaptif di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Sapuan likuiditas: harga menembus ke bawah Low 20-bar, lalu candle berbalik menutup hijau (`C > O`) dan menembus ke atas EMA9.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. **BUY**: $L_i < \text{LL}_{20}[i-1]$ dan $C_i > O_i$ dan $C_i > \text{EMA}_9$
2. **SELL**: $H_i > \text{HH}_{20}[i-1]$ dan $C_i < O_i$ dan $C_i < \text{EMA}_9$

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  Sumbu menembus LL20 -> Candle Hijau Close di atas EMA9 ===> BUY
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
   - **Mode Forex MT5**: $\text{StopDist} = \max(2.0 \times \text{ATR}_{14}(M1), \; 0.0010 \times \text{Price})$ *(floor adaptif 0.10%)*
   - **Mode Spot & Futures**: $\text{StopDist} = \max(2.0 \times \text{ATR}_{14}(M1), \; 0.0035 \times \text{Price})$ *(floor 0.35%)*
   - $\text{TPDist} = 2.0 \times \text{StopDist}$
   - Jika muncul sinyal berlawanan arah (`pos.side != new_side`), posisi lama langsung ditutup (*reverse signal exit*) sebelum posisi baru dibuka.

---

## 5. Audit Risiko, Temuan Bug & Titik Lemah (*CRITICAL AUDIT*)

Hasil pemeriksaan langsung terhadap kode sumber `server/strategies.py`, `server/engine.py`, dan `server/forex_feed.py` menemukan catatan audit spesifik berikut untuk strategi ini:

* **⚠️ Terlalu Ketat Untuk 1 Bar M1 (`0.00%` di UI)**: Dalam satu bar 1-menit yang sama, harga harus menyapu Low 20-menit paling bawah sekaligus menutup melampaui EMA9. Hanya muncul pada sumbu V-reversal ekstrem.
* **ℹ️ Pembaruan Mesin M1 (`0.10% Forex SL Floor` & `1440-Bar History`)**: `engine.py` kini menurunkan batas SL minimum khusus mode **Forex MT5** dari `0.35%` menjadi **`0.10%`** (membuat target & stop jauh lebih proporsional pada pasangan Forex & XAUUSD), sementara mode Spot & Futures menjaga floor `0.35%`. Buffer data M1 diperbesar ke `1440 bar` (24 jam).

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'orderflow_sweep':
def orderflow_sweep(s):
    """Order Flow Liquidity Sweep (1-2 bar sweep + reclaim + volume/wick absorption)."""
    i = s.i
    if i < 22:
        return 0.0
    c, o, l, h, ll, hh, e9 = s.c[i], s.o[i], s.l[i], s.h[i], s.ll20[i - 1], s.hh20[i - 1], s.ema9[i]
    if not _ok(c, o, l, h, ll, hh, e9):
        return 0.0
    rng = max(h - l, 1e-12)
    v, v_sma = s.v[i], s.vol_sma20[i]
    vol_boost = True if (not _ok(v_sma) or v_sma <= 0) else (v >= 1.05 * v_sma)
    swept_low = (l < ll) or (s.l[i - 1] < s.ll20[i - 2])
    swept_high = (h > hh) or (s.h[i - 1] > s.hh20[i - 2])
    if swept_low and c > ll and c > o and (c > e9 or vol_boost or (min(o, c) - l) / rng >= 0.35):
        return 0.80
    if swept_high and c < hh and c < o and (c < e9 or vol_boost or (h - max(o, c)) / rng >= 0.35):
        return -0.80
    return 0.0
```
