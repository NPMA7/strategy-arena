# Spesifikasi Strategi #85: Three Line Strike Pattern (`three_line_strike`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **Three Line Strike Pattern**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#85` · `three_line_strike` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Price action** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (`BarRing` kapasitas 1440 bar / 24 jam) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.8`** | Otomatis berdasarkan cluster `Price action` |
| **Leverage Default** | **`15x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.10\% \text{ Forex} / 0.35\% \text{ Crypto})$ | Floor proteksi adaptif di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Pola pembalikan 4-bar klasik: 3 candle berurutan dengan close makin turun (atau naik), lalu disapu tuntas oleh candle ke-4 ke arah berlawanan menembus Open bar pertama (`o3`), kini dengan toleransi gap pembukaan `0.08 * ATR` agar relevan pada feed real-time M1 kontinu.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. Hitung toleransi $\text{tol} = 0.08 \times \text{ATR}_{14}$.
2. **Bullish Strike (+0.85)**: $C_3 < O_3, C_2 < O_2, C_1 < O_1$, $C_1 < C_2 < C_3$, lalu $C_0 > O_0$, $O_0 \le C_1 + \text{tol}$, dan $C_0 > O_3$.
3. **Bearish Strike (-0.85)**: Simetris terbalik untuk 3 candle bullish + sapuan candle bearish ke-4.

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  3 Candle Turun Beruntun + Candle ke-4 Open <= c1 + 0.08*ATR & Close > o3 ===> BUY (+0.85)
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

* **✅ FIXED (Toleransi ATR Pada Pembukaan Bar ke-4)**: Menambahkan `tol = 0.08 * ATR` pada syarat pembukaan `o0` agar pola dapat terpicu pada chart real-time tanpa gap broker.
* **ℹ️ Pembaruan Mesin M1 (`0.10% Forex SL Floor` & `1440-Bar History`)**: `engine.py` kini menurunkan batas SL minimum khusus mode **Forex MT5** dari `0.35%` menjadi **`0.10%`** (membuat target & stop jauh lebih proporsional pada pasangan Forex & XAUUSD), sementara mode Spot & Futures menjaga floor `0.35%`. Buffer data M1 diperbesar ke `1440 bar` (24 jam).

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'three_line_strike':
def _eval_three_line_strike(o3, c3, o2, c2, o1, c1, o0, c0, tol: float) -> float:
    """Evaluasi pola Three Line Strike pada 4 bar OHLC berurutan."""
    if c3 < o3 and c2 < o2 and c1 < o1 and c1 < c2 < c3:
        if c0 > o0 and c0 > o3 and o0 <= c1 + tol:
            return 0.85
    if c3 > o3 and c2 > o2 and c1 > o1 and c1 > c2 > c3:
        if c0 < o0 and c0 < o3 and o0 >= c1 - tol:
            return -0.85
    return 0.0


def three_line_strike(s):
    """Three Line Strike Price Action Reversal (M1 + konfirmasi M5 completed bars)."""
    if s.i < 4:
        return 0.0
    atr = s.atr14[s.i]
    if not _ok(s.c[s.i], s.o[s.i], atr):
        return 0.0
    tol = max(0.0, 0.08 * atr)
    sc = _eval_three_line_strike(
        s.o[s.i - 3], s.c[s.i - 3],
        s.o[s.i - 2], s.c[s.i - 2],
        s.o[s.i - 1], s.c[s.i - 1],
        s.o[s.i], s.c[s.i],
        tol,
    )
    if sc != 0.0:
        return sc

    # Evaluasi juga pada candle M5 tertutup terbaru (ambil ~30 bar M1 terakhir agar tetap cepat)
    if s.i >= 24:
        import numpy as np
        lo_ix = max(0, s.i - 29)
        ts_sub = s.ts[lo_ix:s.i + 1].astype(np.int64)
        b5 = ts_sub // 300_000
        cur_b = int(b5[-1])
        cur_done = (((int(ts_sub[-1]) // 60_000) + 1) % 5) == 0
        bars_5m = []
        for k in np.unique(b5):
            if int(k) == cur_b and not cur_done:
                continue
            ix = np.flatnonzero(b5 == k)
            if ix.size >= 3:
                bars_5m.append((float(s.o[lo_ix + ix[0]]), float(s.c[lo_ix + ix[-1]])))
        if len(bars_5m) >= 4:
            (o3, c3), (o2, c2), (o1, c1), (o0, c0) = bars_5m[-4:]
            return _eval_three_line_strike(o3, c3, o2, c2, o1, c1, o0, c0, tol * 2.0)
    return 0.0
```
