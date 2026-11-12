# Spesifikasi Strategi #83: Momentum Candle Expansion (`momentum_candle_burst`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **Momentum Candle Expansion**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#83` · `momentum_candle_burst` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Momentum** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (`BarRing` kapasitas 1440 bar / 24 jam) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 2.0`** | Otomatis berdasarkan cluster `Momentum` |
| **Leverage Default** | **`15x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.10\% \text{ Forex} / 0.35\% \text{ Crypto})$ | Floor proteksi adaptif di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Mencari satu candle marubozu bertenaga penuh (range > 1.5×ATR dan body >= 75% dari seluruh panjang candle) searah dengan garis EMA9.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. $\text{Rng} > 1.5\cdot\text{ATR}_{14}$ dan $|C_i - O_i| \ge 0.75\cdot\text{Rng}$
2. **BUY** jika $C_i > O_i$ & $C_i > \text{EMA}_9$, **SELL** jika $C_i < O_i$ & $C_i < \text{EMA}_9$.

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  [Candle Marubozu Full Body >= 75% Range & > 1.5 ATR] + EMA9 ===> ENTRY
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

* **⚠️ Masuk Tanpa Menunggu Retest**: Langsung masuk saat candle penentu ditutup, sehingga posisi rentan terkena pullback sesaat ke 50% candle tersebut (berbeda dengan strategi Fibo Momentum Anda yang sabar menunggu retest!).
* **ℹ️ Pembaruan Mesin M1 (`0.10% Forex SL Floor` & `1440-Bar History`)**: `engine.py` kini menurunkan batas SL minimum khusus mode **Forex MT5** dari `0.35%` menjadi **`0.10%`** (membuat target & stop jauh lebih proporsional pada pasangan Forex & XAUUSD), sementara mode Spot & Futures menjaga floor `0.35%`. Buffer data M1 diperbesar ke `1440 bar` (24 jam).

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'momentum_candle_burst':
def momentum_candle_burst(s):
    """Momentum Candle Expansion (Full-Body Range Expansion selaras EMA9)."""
    c, o, h, l, atr, e9 = s.c[s.i], s.o[s.i], s.h[s.i], s.l[s.i], s.atr14[s.i], s.ema9[s.i]
    if not _ok(c, o, h, l, atr, e9) or atr <= 0:
        return 0.0
    rng = h - l
    body = abs(c - o)
    if rng > 1.35 * atr and body >= 0.68 * rng:
        if c > o and c > e9:
            return 0.85
        if c < o and c < e9:
            return -0.85
    return 0.0
```
