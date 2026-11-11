# Spesifikasi Strategi #73: Heikin-Ashi Trend Continuum (`heikin_ashi_smooth`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **Heikin-Ashi Trend Continuum**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#73` · `heikin_ashi_smooth` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Trend** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (`BarRing` kapasitas 1440 bar / 24 jam) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 2.2`** | Otomatis berdasarkan cluster `Trend` |
| **Leverage Default** | **`8x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.10\% \text{ Forex} / 0.35\% \text{ Crypto})$ | Floor proteksi adaptif di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Menghitung struktur candle **Heikin-Ashi riil** (`HA_Open`, `HA_Close`) secara iteratif selama 10 bar, menyaring tren dengan `ADX > 20`, serta memverifikasi kelanjutan 2 bar HA tanpa sumbu berlawanan (*shaven bottom/top*).

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. Filter kekuatan tren: $\text{ADX}_{14} > 20$.
2. Iterasi 10 bar: $\text{HA\_O}_k = 0.5(\text{HA\_O}_{k-1} + \text{HA\_C}_{k-1})$, $\text{HA\_C}_k = 0.25(O_k+H_k+L_k+C_k)$.
3. **BUY (+0.78)**: 2 bar HA bullish beruntun dan tidak ada sumbu bawah berarti (`< 15%` range) atau $\text{HA\_C}_i > \text{HA\_C}_{i-1}$.
4. **SELL (-0.78)**: 2 bar HA bearish beruntun dan tidak ada sumbu atas berarti atau $\text{HA\_C}_i < \text{HA\_C}_{i-1}$.

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  [ADX > 20] + [2x Heikin-Ashi Bullish Riil Tanpa Lower Wick] ===> BUY (+0.78)
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
   - $\text{TPDist} = 2.2 \times \text{StopDist}$
   - Jika muncul sinyal berlawanan arah (`pos.side != new_side`), posisi lama langsung ditutup (*reverse signal exit*) sebelum posisi baru dibuka.

---

## 5. Audit Risiko, Temuan Bug & Titik Lemah (*CRITICAL AUDIT*)

Hasil pemeriksaan langsung terhadap kode sumber `server/strategies.py`, `server/engine.py`, dan `server/forex_feed.py` menemukan catatan audit spesifik berikut untuk strategi ini:

* **✅ FIXED (Implementasi Formula Heikin-Ashi Riil)**: Bug misnomer lama yang tidak menghitung OHLC Heikin-Ashi telah diperbaiki dengan kalkulasi iteratif `HA_Open` & `HA_Close` sesungguhnya.
* **ℹ️ Pembaruan Mesin M1 (`0.10% Forex SL Floor` & `1440-Bar History`)**: `engine.py` kini menurunkan batas SL minimum khusus mode **Forex MT5** dari `0.35%` menjadi **`0.10%`** (membuat target & stop jauh lebih proporsional pada pasangan Forex & XAUUSD), sementara mode Spot & Futures menjaga floor `0.35%`. Buffer data M1 diperbesar ke `1440 bar` (24 jam).

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'heikin_ashi_smooth':
def heikin_ashi_smooth(s):
    """Heikin-Ashi Smoothed Trend Continuum (kalkulasi HA Open/Close riil)."""
    i = s.i
    if i < 15 or not _ok(s.adx[i]) or s.adx[i] <= 20:
        return 0.0
    ha_o = 0.5 * (s.o[i - 10] + s.c[i - 10])
    ha_c = 0.25 * (s.o[i - 10] + s.h[i - 10] + s.l[i - 10] + s.c[i - 10])
    prev_bull = False
    for k in range(i - 9, i):
        if not _ok(s.o[k], s.h[k], s.l[k], s.c[k]):
            return 0.0
        ha_o = 0.5 * (ha_o + ha_c)
        ha_c = 0.25 * (s.o[k] + s.h[k] + s.l[k] + s.c[k])
        prev_bull = ha_c > ha_o
    cur_ha_o = 0.5 * (ha_o + ha_c)
    cur_ha_c = 0.25 * (s.o[i] + s.h[i] + s.l[i] + s.c[i])
    no_lower_wick = abs(min(cur_ha_o, cur_ha_c) - min(s.l[i], cur_ha_o, cur_ha_c)) < 0.15 * max(s.h[i] - s.l[i], 1e-12)
    no_upper_wick = abs(max(s.h[i], cur_ha_o, cur_ha_c) - max(cur_ha_o, cur_ha_c)) < 0.15 * max(s.h[i] - s.l[i], 1e-12)
    if cur_ha_c > cur_ha_o and prev_bull and (no_lower_wick or cur_ha_c > ha_c):
        return 0.78
    if cur_ha_c < cur_ha_o and not prev_bull and (no_upper_wick or cur_ha_c < ha_c):
        return -0.78
    return 0.0
```
