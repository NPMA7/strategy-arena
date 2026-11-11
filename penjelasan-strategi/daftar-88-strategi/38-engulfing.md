# Spesifikasi Strategi #38: Bullish/Bearish Engulfing (`engulfing`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **Bullish/Bearish Engulfing**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#38` · `engulfing` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Price action** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (`BarRing` kapasitas 1440 bar / 24 jam) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.8`** | Otomatis berdasarkan cluster `Price action` |
| **Leverage Default** | **`15x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.10\% \text{ Forex} / 0.35\% \text{ Crypto})$ | Floor proteksi adaptif di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Pola pembalikan Bullish/Bearish Engulfing klasik dengan dominasi ukuran body (`>= 1.05x` bar sebelumnya) dan toleransi celah pembukaan adaptif berbasis ATR (`0.05 * ATR`) agar kompatibel dengan feed tick kontinu MT5 & Binance.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. $b_1 = |C_{i-1} - O_{i-1}|$, $\;b_2 = |C_i - O_i|$, $\;\text{tol} = 0.05 \times \text{ATR}_{14}$.
2. Syarat dominasi: $b_1 > 0$ dan $b_2 \ge 1.05 \times b_1$.
3. **Bullish (+0.65)**: $C_{i-1} < O_{i-1}$, $C_i > O_i$, $O_i \le C_{i-1} + \text{tol}$, $C_i \ge O_{i-1} - \text{tol}$.
4. **Bearish (-0.65)**: Sebaliknya secara simetris.

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  [Candle i-1 Berlawanan] + [Candle i Body >= 1.05x Menelan Penuh ± 0.05 ATR] ===> ENTRY
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

* **✅ FIXED (Deduplikasi Dari #54 `paint_bar` & Toleransi Gap ATR)**: Menghapus syarat mustahil `o2 < c1` di chart kontinu tanpa gap dan menambahkan `tol = 0.05 * ATR` serta syarat dominasi body `1.05x`.
* **ℹ️ Pembaruan Mesin M1 (`0.10% Forex SL Floor` & `1440-Bar History`)**: `engine.py` kini menurunkan batas SL minimum khusus mode **Forex MT5** dari `0.35%` menjadi **`0.10%`** (membuat target & stop jauh lebih proporsional pada pasangan Forex & XAUUSD), sementara mode Spot & Futures menjaga floor `0.35%`. Buffer data M1 diperbesar ke `1440 bar` (24 jam).

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'engulfing':
def engulfing_pattern(s):
    """Bullish/Bearish Engulfing klasik dengan dominasi body & toleransi ATR kecil."""
    i = s.i
    if i < 2:
        return 0.0
    o1, c1, o2, c2 = s.o[i - 1], s.c[i - 1], s.o[i], s.c[i]
    atr = s.atr14[i]
    if not _ok(o1, c1, o2, c2, atr) or atr <= 0:
        return 0.0
    tol = 0.05 * atr
    b1, b2 = abs(c1 - o1), abs(c2 - o2)
    if b1 <= 0 or b2 < 1.05 * b1:
        return 0.0
    if c1 < o1 and c2 > o2 and o2 <= c1 + tol and c2 >= o1 - tol:
        return 0.65
    if c1 > o1 and c2 < o2 and o2 >= c1 - tol and c2 <= o1 + tol:
        return -0.65
    return 0.0
```
