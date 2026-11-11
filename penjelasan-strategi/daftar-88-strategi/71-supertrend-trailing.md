# Spesifikasi Strategi #71: SuperTrend Dynamic Trailing (`supertrend_trailing`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **SuperTrend Dynamic Trailing**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#71` · `supertrend_trailing` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Trailing** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (`BarRing` kapasitas 1440 bar / 24 jam) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.8`** | Otomatis berdasarkan cluster `Trailing` |
| **Leverage Default** | **`10x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.10\% \text{ Forex} / 0.35\% \text{ Crypto})$ | Floor proteksi adaptif di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Sistem SuperTrend Dynamic Trailing cepat dengan pengali `2.0 x ATR(14)` stateful selama 40 bar terakhir, dipadukan dengan filter arah EMA21 saat terjadi *flip* perubahan tren.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. Hitung band SuperTrend stateful 40 bar: $\text{UB} = \text{HL2} + 2.0\cdot\text{ATR}_{14}$, $\text{LB} = \text{HL2} - 2.0\cdot\text{ATR}_{14}$.
2. **BUY (+0.82)**: Transisi `prev_trend == -1 -> trend == 1` dan $C_i > \text{EMA}_{21}$.
3. **SELL (-0.82)**: Transisi `prev_trend == 1 -> trend == -1` dan $C_i < \text{EMA}_{21}$.

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  [Stateful SuperTrend ATR14 x 2.0 Flip] + [Close Searah EMA21] ===> ENTRY (±0.82)
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

* **✅ FIXED (Implementasi SuperTrend Fast Trailing Stateful)**: Versi lama hanyalah perbandingan EMA21 statis. Kini menggunakan logika SuperTrend stateful 40-bar + filter EMA21.
* **ℹ️ Pembaruan Mesin M1 (`0.10% Forex SL Floor` & `1440-Bar History`)**: `engine.py` kini menurunkan batas SL minimum khusus mode **Forex MT5** dari `0.35%` menjadi **`0.10%`** (membuat target & stop jauh lebih proporsional pada pasangan Forex & XAUUSD), sementara mode Spot & Futures menjaga floor `0.35%`. Buffer data M1 diperbesar ke `1440 bar` (24 jam).

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'supertrend_trailing':
def supertrend_trailing(s):
    """SuperTrend Dynamic Trailing System (ATR14 x 2.0 fast trailing + EMA21 filter)."""
    i = s.i
    if i < 20 or not _ok(s.atr14[i], s.ema21[i]):
        return 0.0
    start = max(1, i - 39)
    final_ub = None
    final_lb = None
    trend = 1
    prev_trend = 1
    for k in range(start, i + 1):
        atr_k, c_k = s.atr14[k], s.c[k]
        if not _ok(atr_k, c_k, s.h[k], s.l[k]) or atr_k <= 0:
            continue
        hl2 = 0.5 * (s.h[k] + s.l[k])
        b_ub = hl2 + 2.0 * atr_k
        b_lb = hl2 - 2.0 * atr_k
        pc = s.c[k - 1]
        if final_ub is None:
            final_ub, final_lb = b_ub, b_lb
            trend = 1 if c_k >= hl2 else -1
            prev_trend = trend
            continue
        prev_trend = trend
        final_ub = b_ub if (b_ub < final_ub or pc > final_ub) else final_ub
        final_lb = b_lb if (b_lb > final_lb or pc < final_lb) else final_lb
        if c_k > final_ub:
            trend = 1
        elif c_k < final_lb:
            trend = -1
    if prev_trend == -1 and trend == 1 and s.c[i] > s.ema21[i]:
        return 0.82
    if prev_trend == 1 and trend == -1 and s.c[i] < s.ema21[i]:
        return -0.82
    return 0.0
```
