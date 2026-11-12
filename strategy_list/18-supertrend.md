# Spesifikasi Strategi #18: SuperTrend ATR (`supertrend`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **SuperTrend ATR**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#18` · `supertrend` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Volatility** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (`BarRing` kapasitas 1440 bar / 24 jam) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.8`** | Otomatis berdasarkan cluster `Volatility` |
| **Leverage Default** | **`10x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.10\% \text{ Forex} / 0.35\% \text{ Crypto})$ | Floor proteksi adaptif di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Menghitung pita SuperTrend `ATR(14) x 3.0` secara **stateful** (band mempertahankan level tinggi/rendah sebelumnya hingga ditembus close) selama jendela 60 bar, memicu sinyal kuat saat terjadi perubahan tren (flip) maupun entri sekunder saat harga pullback ke dekat garis trailing.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. Untuk tiap bar $k \in [\max(1, i-59) \dots i]$: $\text{HL2}_k = \frac{H_k+L_k}{2}$, $\text{BasicUB} = \text{HL2}+3\cdot\text{ATR}_{14}$, $\text{BasicLB} = \text{HL2}-3\cdot\text{ATR}_{14}$.
2. Band stateful: `final_ub` hanya boleh turun (`prev_c <= final_ub`), `final_lb` hanya boleh naik (`prev_c >= final_lb`).
3. **Flip Signal (±0.80)**: Perubahan `prev_trend -> trend` (`c_k > final_ub` -> UP, `c_k < final_lb` -> DOWN).
4. **Pullback Signal (±0.35)**: Dalam tren naik aktif (`trend == 1`) ketika $\text{final\_lb} < C_i < \text{EMA}_{21}$ (dan sebaliknya).

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  [Stateful Trailing Band 60-bar ATR14 x 3.0]
  Breakout FinalUB (Flip -1 -> +1) ===> BUY (+0.80) | Pullback > FinalLB & < EMA21 ===> BUY (+0.35)
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

* **✅ FIXED (Dead Code & Non-Stateful Band Diperbaiki)**: Bug lama berupa kondisi unreachable dan band statis telah diganti dengan loop SuperTrend stateful `14 x 3.0 ATR` yang akurat mengikuti logika TradingView.
* **ℹ️ Pembaruan Mesin M1 (`0.10% Forex SL Floor` & `1440-Bar History`)**: `engine.py` kini menurunkan batas SL minimum khusus mode **Forex MT5** dari `0.35%` menjadi **`0.10%`** (membuat target & stop jauh lebih proporsional pada pasangan Forex & XAUUSD), sementara mode Spot & Futures menjaga floor `0.35%`. Buffer data M1 diperbesar ke `1440 bar` (24 jam).

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'supertrend':
def supertrend(s):
    """SuperTrend 14 x 3.0 ATR stateful trailing band."""
    i = s.i
    if i < 20 or not _ok(s.atr14[i]):
        return 0.0
    start = max(1, i - 59)
    final_ub = None
    final_lb = None
    trend = 1
    prev_trend = 1
    for k in range(start, i + 1):
        atr_k = s.atr14[k]
        c_k = s.c[k]
        if not _ok(atr_k, c_k, s.h[k], s.l[k]) or atr_k <= 0:
            continue
        hl2 = 0.5 * (s.h[k] + s.l[k])
        basic_ub = hl2 + 3.0 * atr_k
        basic_lb = hl2 - 3.0 * atr_k
        prev_c = s.c[k - 1]
        if final_ub is None:
            final_ub = basic_ub
            final_lb = basic_lb
            trend = 1 if c_k >= hl2 else -1
            prev_trend = trend
            continue
        prev_trend = trend
        final_ub = basic_ub if (basic_ub < final_ub or prev_c > final_ub) else final_ub
        final_lb = basic_lb if (basic_lb > final_lb or prev_c < final_lb) else final_lb
        if c_k > final_ub:
            trend = 1
        elif c_k < final_lb:
            trend = -1
    if final_ub is None or final_lb is None:
        return 0.0
    if prev_trend == -1 and trend == 1:
        return 0.8
    if prev_trend == 1 and trend == -1:
        return -0.8
    if _ok(s.ema21[i]):
        if trend == 1 and s.c[i] > final_lb and s.c[i] < s.ema21[i]:
            return 0.35
        if trend == -1 and s.c[i] < final_ub and s.c[i] > s.ema21[i]:
            return -0.35
    return 0.0
```
