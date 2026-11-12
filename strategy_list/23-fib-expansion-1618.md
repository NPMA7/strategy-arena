# Spesifikasi Strategi #23: Fib Extension 1.618 (`fib_expansion_1618`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **Fib Extension 1.618**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#23` · `fib_expansion_1618` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Fibonacci** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (`BarRing` kapasitas 1440 bar / 24 jam) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.8`** | Otomatis berdasarkan cluster `Fibonacci` |
| **Leverage Default** | **`12x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.10\% \text{ Forex} / 0.35\% \text{ Crypto})$ | Floor proteksi adaptif di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Mengejar momentum saat harga menembus melampaui ekstensi 1.272 (27.2% di luar rentang 20 bar sebelumnya) dengan konfirmasi EMA21.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. $\text{TargetBull} = \text{High}_{20} + 0.272 \times \text{Rng}_{20}$
2. **BUY**: $C_i > \text{TargetBull}$ dan $C_{i-1} \le \text{TargetBull}$ dan $C_i > \text{EMA}_{21}$

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  +27.2% Ext  -------------------  <-- Breakout di bar i = BUY
  High20      ===================
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
   - $\text{TPDist} = 1.8 \times \text{StopDist}$
   - Jika muncul sinyal berlawanan arah (`pos.side != new_side`), posisi lama langsung ditutup (*reverse signal exit*) sebelum posisi baru dibuka.

---

## 5. Audit Risiko, Temuan Bug & Titik Lemah (*CRITICAL AUDIT*)

Hasil pemeriksaan langsung terhadap kode sumber `server/strategies.py`, `server/engine.py`, dan `server/forex_feed.py` menemukan catatan audit spesifik berikut untuk strategi ini:

* **⚠️ Ambiguitas Target 1.272 vs Nama 1.618**: Nama strategi adalah `Fib Extension 1.618`, tetapi di kode target breakout yang dihitung adalah `0.272` (ekstensi `1.272`). Selain itu, membutuhkan satu candle M1 menembus 27.2% di atas High 20-bar yang sudah melesat sering kali berarti entry saat candle sudah sangat overextended.
* **ℹ️ Pembaruan Mesin M1 (`0.10% Forex SL Floor` & `1440-Bar History`)**: `engine.py` kini menurunkan batas SL minimum khusus mode **Forex MT5** dari `0.35%` menjadi **`0.10%`** (membuat target & stop jauh lebih proporsional pada pasangan Forex & XAUUSD), sementara mode Spot & Futures menjaga floor `0.35%`. Buffer data M1 diperbesar ke `1440 bar` (24 jam).

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'fib_expansion_1618':
def fib_expansion_1618(s):
    """Breakout ekspansi Fibonacci 1.272–1.618 ekstensi dengan dorongan momentum."""
    i = s.i
    if i < 40:
        return 0.0
    recent_hi = float(s.h[i - 20:i].max())
    recent_lo = float(s.l[i - 20:i].min())
    rng = recent_hi - recent_lo
    if rng <= 0:
        return 0.0
    c = s.c[i]
    # Breakout ke zona ekstensi 1.272
    target_ext_bull = recent_hi + rng * 0.272
    target_ext_bear = recent_lo - rng * 0.272
    if c > target_ext_bull and s.c[i - 1] <= target_ext_bull and c > s.ema21[i]:
        return 0.7
    if c < target_ext_bear and s.c[i - 1] >= target_ext_bear and c < s.ema21[i]:
        return -0.7
    return 0.0
```
