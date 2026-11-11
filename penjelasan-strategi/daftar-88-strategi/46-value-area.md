# Spesifikasi Strategi #46: Value Area Auction (`value_area`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **Value Area Auction**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#46` · `value_area` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Volume profile** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (`BarRing` kapasitas 1440 bar / 24 jam) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.8`** | Otomatis berdasarkan cluster `Volume profile` |
| **Leverage Default** | **`10x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.10\% \text{ Forex} / 0.35\% \text{ Crypto})$ | Floor proteksi adaptif di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Mengimplementasikan lelang Market/Volume Profile nyata menggunakan histogram 12-bin terbobot volume selama 90 bar terakhir: menentukan Point of Control (POC) serta batas 70% Value Area (VAH & VAL) lalu merespons penolakan kembali masuk dari luar area nilai.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. Bagi rentang $[\min(C_{90}), \max(C_{90})]$ ke dalam 12 bin volume (`np.histogram`, weights=$V$).
2. Mulai ekspansi serakah (*greedy expansion*) dari bin POC hingga mencakup $\ge 70\%$ total volume -> peroleh `VAL` dan `VAH`.
3. **BUY (+0.70)**: $C_i < \text{VAL}$ dan $C_i > O_i$ (penolakan naik dari bawah Value Area Low).
4. **SELL (-0.70)**: $C_i > \text{VAH}$ dan $C_i < O_i$ (penolakan turun dari atas Value Area High).

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  Above VAH + Red Reject  ===> SELL (-0.70)
  [VAH --- POC (70% Vol) --- VAL]
  Below VAL + Bull Reject ===> BUY  (+0.70)
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

* **✅ FIXED (Deduplikasi Dari `vwap_band` #24)**: Sebelumnya memanggil `vwap_band(s)` sehingga PnL identik mutlak. Kini mengimplementasikan Volume Profile Histogram 12-bin + VAH/VAL/POC secara independen.
* **ℹ️ Pembaruan Mesin M1 (`0.10% Forex SL Floor` & `1440-Bar History`)**: `engine.py` kini menurunkan batas SL minimum khusus mode **Forex MT5** dari `0.35%` menjadi **`0.10%`** (membuat target & stop jauh lebih proporsional pada pasangan Forex & XAUUSD), sementara mode Spot & Futures menjaga floor `0.35%`. Buffer data M1 diperbesar ke `1440 bar` (24 jam).

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'value_area':
def value_area_profile(s):
    """Volume Profile Auction: POC & 70% Value Area (VAH/VAL) dari distribusi volume 90 bar."""
    import numpy as np
    i = s.i
    if i < 60:
        return 0.0
    a = max(0, i - 89)
    closes = s.c[a:i + 1]
    vols = s.v[a:i + 1]
    lo, hi = float(closes.min()), float(closes.max())
    if hi <= lo:
        return 0.0
    bins = 12
    weights = np.where(vols > 0, vols, 1.0)
    hist, edges = np.histogram(closes, bins=bins, range=(lo, hi), weights=weights)
    tot = float(hist.sum())
    if tot <= 0:
        return 0.0
    poc_idx = int(np.argmax(hist))
    acc = float(hist[poc_idx])
    l_idx = r_idx = poc_idx
    while acc < 0.70 * tot and (l_idx > 0 or r_idx < bins - 1):
        left_v = float(hist[l_idx - 1]) if l_idx > 0 else -1.0
        right_v = float(hist[r_idx + 1]) if r_idx < bins - 1 else -1.0
        if left_v >= right_v:
            l_idx -= 1
            acc += left_v
        else:
            r_idx += 1
            acc += right_v
    val, vah = float(edges[l_idx]), float(edges[r_idx + 1])
    c, o = s.c[i], s.o[i]
    if c < val and c > o:
        return 0.7
    if c > vah and c < o:
        return -0.7
    return 0.0
```
