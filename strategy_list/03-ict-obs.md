# Spesifikasi Strategi #3: ICT Order Block Sweep (`ict_obs`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **ICT Order Block Sweep**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#3` · `ict_obs` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **ICT** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (`BarRing` kapasitas 1440 bar / 24 jam) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.8`** | Otomatis berdasarkan cluster `ICT` |
| **Leverage Default** | **`15x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.10\% \text{ Forex} / 0.35\% \text{ Crypto})$ | Floor proteksi adaptif di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Deteksi Liquidity Sweep pada Swing Low/High 15-bar sebelumnya yang langsung diikuti candle impulsif (*engulfing displacement*) sebagai Order Block valid, lalu menunggu harga kembali (*unmitigated retest*) masuk ke zona `[L_k, H_k]` OB tersebut dengan penutupan searah.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. Scan $k \in [i-2 \dots i-10]$ (mundur hingga 10 bar).
2. **Bullish Sweep OB**: $L_k < \min(L_{k-15..k-1})$, $C_k > O_k$, diikuti $C_{k+1} > H_k$.
3. **Unmitigated**: $\min(L_{k+1..i-1}) \ge L_k$.
4. **Entry BUY (+0.78)**: $L_i \le H_k$ dan $C_i \ge L_k$ dan $C_i > O_i$ (mirror simetris untuk Bearish Sweep OB `-0.78`).

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  Swing Low 15-bar ---> [Sweep L_k + Engulf k+1] ===> Retest Unmitigated [L_k..H_k] + Close Searah => ENTRY
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

* **✅ FIXED (Deduplikasi & Implementasi Sweep OB Sejati)**: Bug lama di mana `ict_obs` menunjuk `fractal_break` (#56) telah diperbaiki. Kini menjalankan `ict_orderblock_sweep(s)` independen dengan deteksi *liquidity sweep* 15-bar + validasi *unmitigated Order Block*.
* **ℹ️ Pembaruan Mesin M1 (`0.10% Forex SL Floor` & `1440-Bar History`)**: `engine.py` kini menurunkan batas SL minimum khusus mode **Forex MT5** dari `0.35%` menjadi **`0.10%`** (membuat target & stop jauh lebih proporsional pada pasangan Forex & XAUUSD), sementara mode Spot & Futures menjaga floor `0.35%`. Buffer data M1 diperbesar ke `1440 bar` (24 jam).

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'ict_obs':
def ict_orderblock_sweep(s):
    """ICT Order Block Sweep: bar sebelumnya menyapu swing low/high lalu dimitigasi sebagai OB."""
    i = s.i
    if i < 20:
        return 0.0
    atr = s.atr14[i]
    c, o, h, l = s.c[i], s.o[i], s.h[i], s.l[i]
    if not _ok(atr, c, o, h, l) or atr <= 0:
        return 0.0
    for k in range(i - 2, max(i - 10, 15), -1):
        ll_prev = float(s.l[k - 15:k].min())
        if s.l[k] < ll_prev and s.c[k] > s.o[k] and s.c[k + 1] > s.h[k]:
            if float(s.l[k + 1:i].min()) >= s.l[k] and l <= s.h[k] and c >= s.l[k] and c > o:
                return 0.78
            break
    for k in range(i - 2, max(i - 10, 15), -1):
        hh_prev = float(s.h[k - 15:k].max())
        if s.h[k] > hh_prev and s.c[k] < s.o[k] and s.c[k + 1] < s.l[k]:
            if float(s.h[k + 1:i].max()) <= s.h[k] and h >= s.l[k] and c <= s.h[k] and c < o:
                return -0.78
            break
    return 0.0
```
