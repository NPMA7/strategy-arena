# Spesifikasi Strategi #89: Volume Spread Analysis (VSA) (`volume_spread_analysis`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **Volume Spread Analysis (VSA)**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#89` · `volume_spread_analysis` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Order flow** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (`BarRing` kapasitas 1440 bar / 24 jam) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 2.0`** | Otomatis berdasarkan cluster `Order flow` |
| **Leverage Default** | **`15x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.10\% \text{ Forex} / 0.35\% \text{ Crypto})$ | Floor proteksi adaptif di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Volume Spread Analysis (VSA) sejati: mendeteksi candle berentang lebar (`> 1.5 ATR`) yang dikonfirmasi oleh **lonjakan volume `> 1.15x VolSMA(20)`** serta penutupan absorpsi kuat (`>= 55%` dari range bar searah).

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. Spread lebar: $(H_i - L_i) > 1.5 \times \text{ATR}_{14}$.
2. Konfirmasi Volume (bila tersedia): $V_i > 1.15 \times \text{VolSMA}_{20}$.
3. **BUY (+0.80)**: $(C_i - L_i)/(H_i - L_i) \ge 0.55$ dan $C_i > O_i$.
4. **SELL (-0.80)**: $(H_i - C_i)/(H_i - L_i) \ge 0.55$ dan $C_i < O_i$.

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  [Spread > 1.5 ATR] + [Volume > 1.15x VolSMA20] + [Absorption Close >= 55%] ===> ENTRY
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

* **✅ FIXED (Integrasi Volume Riil MT5 & Filter Spike `1.15x`)**: Sebelumnya tidak memeriksa `s.v` sama sekali. Kini menggunakan volume tick riil MT5 (dan volume Binance di Kripto) sebagai syarat konfirmasi VSA.
* **ℹ️ Pembaruan Mesin M1 (`0.10% Forex SL Floor` & `1440-Bar History`)**: `engine.py` kini menurunkan batas SL minimum khusus mode **Forex MT5** dari `0.35%` menjadi **`0.10%`** (membuat target & stop jauh lebih proporsional pada pasangan Forex & XAUUSD), sementara mode Spot & Futures menjaga floor `0.35%`. Buffer data M1 diperbesar ke `1440 bar` (24 jam).

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'volume_spread_analysis':
def volume_spread_analysis(s):
    """Volume Spread Analysis (VSA): Wide Spread Momentum + Stopping Volume Climax."""
    i = s.i
    c, o, h, l, atr, v, v_sma, e21 = (
        s.c[i], s.o[i], s.h[i], s.l[i], s.atr14[i], s.v[i], s.vol_sma20[i], s.ema21[i]
    )
    if not _ok(c, o, h, l, atr) or atr <= 0:
        return 0.0
    rng = h - l
    if rng <= 0:
        return 0.0
    has_vol = bool(_ok(v_sma) and v_sma > 0)
    vol_ok = True if not has_vol else (v > 1.15 * v_sma)
    if rng > 1.35 * atr and vol_ok:
        if (c - l) / rng >= 0.55 and c > o:
            return 0.80
        if (h - c) / rng >= 0.55 and c < o:
            return -0.80
    # Stopping Volume Climax (volume spike tinggi + penolakan ekor kuat di sisi bawah/atas EMA21)
    if has_vol and v > 1.45 * v_sma and _ok(e21):
        if (c - l) / rng >= 0.62 and c <= e21:
            return 0.78
        if (h - c) / rng >= 0.62 and c >= e21:
            return -0.78
    return 0.0
```
