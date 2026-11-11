# Spesifikasi Strategi #80: ICT Fair Value Gap (FVG) (`fx_ict_fair_value_gap`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **ICT Fair Value Gap (FVG)**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#80` · `fx_ict_fair_value_gap` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **ICT** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (1-Menit Bar Closed via `BarRing`) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.8`** | Otomatis berdasarkan cluster `ICT` |
| **Leverage Default** | **`1x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.35\% \times \text{Harga})$ | Floor proteksi minimum 0.35% di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Dimaksudkan mendeteksi ICT Fair Value Gap (FVG) lalu masuk saat retest.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

`gap_low, gap_high = s.h[i-2], s.l[i-1]`

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  [BUG INDEXING]: Membandingkan High[i-2] dengan Low[i-1] (bar bersebelahan!)
  seharusnya High[i-3] dengan Low[i-1] (celah 3 candle)!
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

* **🚨 CRITICAL CODE BUG (Salah Indeks Bar -> 0.00% / 0 Transaksi!)**: 
   Lihat baris 979 & 985: `gap_low, gap_high = s.h[s.i - 2], s.l[s.i - 1]`. 
   FVG 3-candle yang benar harus menyisakan **1 candle pemisah di tengah** (membandingkan `High[i-3]` dengan `Low[i-1]`). Membandingkan `High[i-2]` dan `Low[i-1]` (dua bar yang menempel langsung!) mengharuskan adanya **celah udara fisik (*price gap*)** di antara penutupan dan pembukaan candle berikutnya! Di pasar kontinu 24 jam hal ini nyaris tak pernah terjadi, sehingga `#48 ICT Fair Value Gap (FVG)` macet permanen di **`0.00%`**!
* **⚠️ Catatan Umum Mesin M1 (`0.35% Minimum SL Floor`)**: Karena sinyal dievaluasi pada bar **1-menit (`M1`)**, sedangkan `engine.py` memaksa jarak Stop Loss minimal `0.35%` (~143 pips pada XAUUSD atau ~39 pips pada EURUSD), strategi jangka pendek M1 harus menahan fluktuasi lebar yang kerap tidak sebanding dengan target scalping-nya.

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'fx_ict_fair_value_gap':
def fx_ict_fair_value_gap(s):
    """ICT Fair Value Gap (FVG) Imbalance Retest."""
    if s.i < 5:
        return 0.0
    c, o, h, l = s.c[s.i], s.o[s.i], s.h[s.i], s.l[s.i]
    h2, l2, h0, l0 = s.h[s.i - 2], s.l[s.i - 2], s.h[s.i], s.l[s.i]
    if not _ok(c, o, h, l, h2, l2):
        return 0.0
    # Bullish FVG created at bar i-1 (low[i-1] > high[i-3] or low[i] > high[i-2])
    gap_low, gap_high = s.h[s.i - 2], s.l[s.i - 1]
    if gap_high > gap_low:
        # Price dips into FVG and closes bullish
        if l <= gap_high and c >= gap_low and c > o:
            return 0.80
    # Bearish FVG (high[i-1] < low[i-3] or high[i-1] < low[i-2])
    bgap_high, bgap_low = s.l[s.i - 2], s.h[s.i - 1]
    if bgap_high > bgap_low:
        if h >= bgap_low and c <= bgap_high and c < o:
            return -0.80
    return 0.0
```
