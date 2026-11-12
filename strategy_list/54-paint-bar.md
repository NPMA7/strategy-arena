# Spesifikasi Strategi #54: Paint Bar Pattern (`paint_bar`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **Paint Bar Pattern**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#54` · `paint_bar` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Price action** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (`BarRing` kapasitas 1440 bar / 24 jam) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.8`** | Otomatis berdasarkan cluster `Price action` |
| **Leverage Default** | **`15x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.10\% \text{ Forex} / 0.35\% \text{ Crypto})$ | Floor proteksi adaptif di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Implementasi sejati **3-Bar Key Reversal (Outside Sweep & Close Reversal)**: candle `i` terlebih dahulu menyapu likuiditas di luar ekstrem 2 candle sebelumnya (`L_i < min(L1, L2)` atau `H_i > max(H1, H2)`) lalu berbalik kuat menutup menembus sisi sebaliknya.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. $h_1, h_2 = H_{i-1}, H_{i-2}$ dan $l_1, l_2 = L_{i-1}, L_{i-2}$.
2. **BUY (+0.70)**: $L_i < \min(l_1, l_2)$ dan $C_i > \max(h_1, h_2)$ dan $C_i > O_i$.
3. **SELL (-0.70)**: $H_i > \max(h_1, h_2)$ dan $C_i < \min(l_1, l_2)$ dan $C_i < O_i$.

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  Sweep < min(Low i-1, i-2) ===> Reversal Close > max(High i-1, i-2) ===> BUY (+0.70)
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

* **✅ FIXED (Deduplikasi Dari #38 `engulfing` Diperbaiki)**: Sebelumnya identik 100% dengan `engulfing` dan mati di 0%. Kini menjalankan pola *3-Bar Key Reversal* independen.
* **ℹ️ Pembaruan Mesin M1 (`0.10% Forex SL Floor` & `1440-Bar History`)**: `engine.py` kini menurunkan batas SL minimum khusus mode **Forex MT5** dari `0.35%` menjadi **`0.10%`** (membuat target & stop jauh lebih proporsional pada pasangan Forex & XAUUSD), sementara mode Spot & Futures menjaga floor `0.35%`. Buffer data M1 diperbesar ke `1440 bar` (24 jam).

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'paint_bar':
def paint_bar(s):
    """3-Bar Key Reversal / Paint-Bar: sweep high/low 2 bar lalu tutup berbalik menembus kedua bar."""
    i = s.i
    if i < 3:
        return 0.0
    h1, h2 = s.h[i - 1], s.h[i - 2]
    l1, l2 = s.l[i - 1], s.l[i - 2]
    c, l_now, h_now = s.c[i], s.l[i], s.h[i]
    if l_now < min(l1, l2) and c > max(h1, h2) and c > s.o[i]:
        return 0.7
    if h_now > max(h1, h2) and c < min(l1, l2) and c < s.o[i]:
        return -0.7
    return 0.0
```
