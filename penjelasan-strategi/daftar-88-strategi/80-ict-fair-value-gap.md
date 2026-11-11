# Spesifikasi Strategi #80: ICT Fair Value Gap (FVG) (`ict_fair_value_gap`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **ICT Fair Value Gap (FVG)**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#80` · `ict_fair_value_gap` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **ICT** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (`BarRing` kapasitas 1440 bar / 24 jam) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.8`** | Otomatis berdasarkan cluster `ICT` |
| **Leverage Default** | **`12x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.10\% \text{ Forex} / 0.35\% \text{ Crypto})$ | Floor proteksi adaptif di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Deteksi **3-Candle Fair Value Gap (FVG)** sejati (`Low[k] > High[k-2]` untuk Bullish Gap, `High[k] < Low[k-2]` untuk Bearish Gap) minimal `0.2 ATR` dalam 12 bar terakhir, memastikan gap belum terisi penuh (*unmitigated*), lalu masuk saat harga saat ini melakukan mitigasi aktif di dalam gap.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. Scan $k \in [i-1 \dots i-12]$ (gap terbentuk dari triplet `k-2`, `k-1`, `k`).
2. **Bullish FVG (+0.80)**: $\text{gap\_low} = H_{k-2}$, $\text{gap\_high} = L_k$, selisih $\ge 0.2\cdot\text{ATR}$; pastikan belum pernah ditutup di bawah `gap_low` pada $[k+1..i-1]$; entry saat $L_i \le \text{gap\_high}$ dan $C_i \ge \text{gap\_low}$ dengan $C_i > O_i$.
3. **Bearish FVG (-0.80)**: Simetris menggunakan $L_{k-2}$ dan $H_k$.

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  [Candle k-2 High]  <-- FVG Gap (>= 0.2 ATR) -->  [Candle k Low] ===> Mitigasi Aktif di Bar [i]
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

* **✅ FIXED (Bug Indeks Statis & Kondisi Mustahil Diperbaiki)**: Bug lama membandingkan `s.i - 1` vs `s.i - 3` yang menyebabkan 0% transaksi kini diganti dengan scan FVG 3-candle berumur hingga 12 bar beserta cek mitigasi.
* **ℹ️ Pembaruan Mesin M1 (`0.10% Forex SL Floor` & `1440-Bar History`)**: `engine.py` kini menurunkan batas SL minimum khusus mode **Forex MT5** dari `0.35%` menjadi **`0.10%`** (membuat target & stop jauh lebih proporsional pada pasangan Forex & XAUUSD), sementara mode Spot & Futures menjaga floor `0.35%`. Buffer data M1 diperbesar ke `1440 bar` (24 jam).

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'ict_fair_value_gap':
def ict_fair_value_gap(s):
    """ICT Fair Value Gap (FVG) Imbalance 3-Candle Mitigation."""
    i = s.i
    if i < 6:
        return 0.0
    c, o, h, l, atr = s.c[i], s.o[i], s.h[i], s.l[i], s.atr14[i]
    if not _ok(c, o, h, l, atr) or atr <= 0:
        return 0.0
    for k in range(i - 1, max(i - 12, 2), -1):
        # Bullish 3-candle FVG: low[k] > high[k-2]
        gap_low, gap_high = s.h[k - 2], s.l[k]
        if gap_high - gap_low >= 0.2 * atr:
            # Pastikan gap belum terisi penuh sebelumnya
            filled = (k + 1 < i) and (float(s.l[k + 1:i].min()) <= gap_low)
            if not filled and l <= gap_high and c >= gap_low and c > o:
                return 0.80
        # Bearish 3-candle FVG: high[k] < low[k-2]
        bgap_low, bgap_high = s.h[k], s.l[k - 2]
        if bgap_high - bgap_low >= 0.2 * atr:
            filled = (k + 1 < i) and (float(s.h[k + 1:i].max()) >= bgap_high)
            if not filled and h >= bgap_low and c <= bgap_high and c < o:
                return -0.80
    return 0.0
```
