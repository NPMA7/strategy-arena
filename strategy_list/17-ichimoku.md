# Spesifikasi Strategi #17: Ichimoku Kumo (`ichimoku`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **Ichimoku Kumo**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#17` · `ichimoku` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Trend** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (`BarRing` kapasitas 1440 bar / 24 jam) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 2.2`** | Otomatis berdasarkan cluster `Trend` |
| **Leverage Default** | **`8x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.10\% \text{ Forex} / 0.35\% \text{ Crypto})$ | Floor proteksi adaptif di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Menggunakan Tenkan-sen (9), Kijun-sen (26), dan Awan Kumo (Senkou Span A & B) untuk mendeteksi konfirmasi tren penuh di atas/bawah awan.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. $\text{Conv} = \text{Mid}(\text{HL}_9)$, $\text{Base} = \text{Mid}(\text{HL}_{26})$
2. $\text{SpanA} = \frac{\text{Conv} + \text{Base}}{2}$, $\text{SpanB} = \text{Mid}(\text{HL}_{52})$
3. **BUY**: $C_i > \max(\text{SpanA}, \text{SpanB})$ dan $\text{Conv} > \text{Base}$

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  Harga (C)  =====> Di atas Kumo Top + Conv > Base ===> BUY (+0.8)
  [Awan Kumo: Span A .. Span B]
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

* **🚨 BUG PERHITUNGAN KUMO (Missing 26-Bar Shift)**: Pada Ichimoku asli, Awan Kumo yang memandu harga saat ini adalah nilai Span A dan Span B yang dihitung **26 bar yang lalu** (diplot 26 periode ke depan). Kode menghitung `span_a` dan `span_b` di bar `i` saat ini tanpa pergeseran (*shift*) 26 bar, sehingga sensitivitas awan menjadi tidak standar.
* **⚠️ Entry Berkelanjutan**: Karena kondisi `c > top and conv > base` terus bernilai True di sepanjang tren naik, sinyal selalu aktif setiap bar.
* **ℹ️ Pembaruan Mesin M1 (`0.10% Forex SL Floor` & `1440-Bar History`)**: `engine.py` kini menurunkan batas SL minimum khusus mode **Forex MT5** dari `0.35%` menjadi **`0.10%`** (membuat target & stop jauh lebih proporsional pada pasangan Forex & XAUUSD), sementara mode Spot & Futures menjaga floor `0.35%`. Buffer data M1 diperbesar ke `1440 bar` (24 jam).

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'ichimoku':
def ichimoku(s):
    i = s.i
    if i < 55:
        return 0.0
    conv = (float(s.h[i - 8:i + 1].max()) + float(s.l[i - 8:i + 1].min())) / 2
    base = (float(s.h[i - 25:i + 1].max()) + float(s.l[i - 25:i + 1].min())) / 2
    span_a = (conv + base) / 2
    span_b = (float(s.h[i - 51:i + 1].max()) + float(s.l[i - 51:i + 1].min())) / 2
    top, bot = max(span_a, span_b), min(span_a, span_b)
    c = s.c[i]
    if c > top and conv > base:
        return 0.8
    if c < bot and conv < base:
        return -0.8
    return 0.0
```
