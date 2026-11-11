# Spesifikasi Strategi #22: Fib Golden Pocket 61.8 (`fib_golden_pocket`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **Fib Golden Pocket 61.8**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#22` · `fib_golden_pocket` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Fibonacci** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (1-Menit Bar Closed via `BarRing`) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.8`** | Otomatis berdasarkan cluster `Fibonacci` |
| **Leverage Default** | **`10x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.35\% \times \text{Harga})$ | Floor proteksi minimum 0.35% di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Menangkap pantulan tepat di zona sakral Golden Pocket (60%–68% retracement) dari rentang 60 bar dengan konfirmasi candle searah dan filter EMA50.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. **Bullish Depth**: $\frac{\text{High}_{60} - C_i}{\text{Rng}_{60}} \in [0.60, 0.68]$ dan $C_i > \text{EMA}_{50}$ dan $C_i > O_i$
2. **Bearish Depth**: $\frac{C_i - \text{Low}_{60}}{\text{Rng}_{60}} \in [0.60, 0.68]$ dan $C_i < \text{EMA}_{50}$ dan $C_i < O_i$

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  High60 -----------
  Retest  60% - 68%  <=== Golden Pocket + Candle Searah + EMA50
  Low60  -----------
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

* **⚠️ Syarat Saling Berbenturan (Terlalu Ketat -> 0 Trades di UI!)**: Jika harga sudah terkoreksi 60%–68% turun dari puncak 60-bar terakhir, secara matematis harga almost always sudah jatuh **di bawah** `EMA50`! Namun syarat memaksa `c > ema50` di saat yang sama. Akibatnya sinyal hampir tidak pernah lolos (`0.00% / $1,000` di screenshot).
* **⚠️ Catatan Umum Mesin M1 (`0.35% Minimum SL Floor`)**: Karena sinyal dievaluasi pada bar **1-menit (`M1`)**, sedangkan `engine.py` memaksa jarak Stop Loss minimal `0.35%` (~143 pips pada XAUUSD atau ~39 pips pada EURUSD), strategi jangka pendek M1 harus menahan fluktuasi lebar yang kerap tidak sebanding dengan target scalping-nya.

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'fib_golden_pocket':
def fib_golden_pocket(s):
    """Entry di Golden Pocket (61.8% - 65% retracement) dari swing 60 bar dengan konfirmasi candlestick & EMA50."""
    i = s.i
    if i < 60:
        return 0.0
    swing_hi = float(s.h[i - 59:i + 1].max())
    swing_lo = float(s.l[i - 59:i + 1].min())
    rng = swing_hi - swing_lo
    if rng <= 0:
        return 0.0
    c = s.c[i]
    e50 = s.ema50[i]
    if not _ok(e50):
        return 0.0
    # Bullish GP: koreksi turun 61.8% - 66% dari swing low ke swing high
    fib_depth_bull = (swing_hi - c) / rng
    if 0.60 <= fib_depth_bull <= 0.68 and c > e50 and c > s.o[i]:
        return 0.75
    # Bearish GP: koreksi naik 61.8% - 66% dari swing high ke swing low
    fib_depth_bear = (c - swing_lo) / rng
    if 0.60 <= fib_depth_bear <= 0.68 and c < e50 and c < s.o[i]:
        return -0.75
    return 0.0
```
