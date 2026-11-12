# Spesifikasi Strategi #14: MACD Divergence (`macd_div`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **MACD Divergence**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#14` · `macd_div` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Momentum** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (`BarRing` kapasitas 1440 bar / 24 jam) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 2.0`** | Otomatis berdasarkan cluster `Momentum` |
| **Leverage Default** | **`12x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.10\% \text{ Forex} / 0.35\% \text{ Crypto})$ | Floor proteksi adaptif di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Mendeteksi divergensi klasik antara harga dan garis MACD pada dua jendela waktu yang **benar-benar terpisah (disjoint)**: membandingkan jendela awal `[i-30..i-15]` vs jendela terkini `[i-14..i]`, dikonfirmasi dengan penutupan harga menembus EMA9.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. Jendela Lama `prev = [i-30 : i-14]` (16 bar), Jendela Baru `now = [i-14 : i+1]` (15 bar).
2. **Bullish Divergence (+0.65)**: $\min(L_{\text{now}}) < \min(L_{\text{prev}})$ dan $\min(\text{MACD}_{\text{now}}) > \min(\text{MACD}_{\text{prev}})$ serta $C_i > \text{EMA}_9$.
3. **Bearish Divergence (-0.65)**: $\max(H_{\text{now}}) > \max(H_{\text{prev}})$ dan $\max(\text{MACD}_{\text{now}}) < \max(\text{MACD}_{\text{prev}})$ serta $C_i < \text{EMA}_9$.

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  [Prev Window i-30..i-15]  |  [Now Window i-14..i] (Disjoint 0-overlap)
  Price Lower Low  +  MACD Higher Low  +  Close > EMA9 ===> BUY (+0.65)
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
   - $\text{TPDist} = 2.0 \times \text{StopDist}$
   - Jika muncul sinyal berlawanan arah (`pos.side != new_side`), posisi lama langsung ditutup (*reverse signal exit*) sebelum posisi baru dibuka.

---

## 5. Audit Risiko, Temuan Bug & Titik Lemah (*CRITICAL AUDIT*)

Hasil pemeriksaan langsung terhadap kode sumber `server/strategies.py`, `server/engine.py`, dan `server/forex_feed.py` menemukan catatan audit spesifik berikut untuk strategi ini:

* **✅ FIXED (Bug Window Overlap 15-Bar Diperbaiki)**: Slice `[i-25:i-5]` vs `[i-20:i+1]` yang sebelumnya tumpang-tindih 15 bar kini diganti menjadi `[i-30:i-14]` vs `[i-14:i+1]` yang saling lepas sepenuhnya.
* **ℹ️ Pembaruan Mesin M1 (`0.10% Forex SL Floor` & `1440-Bar History`)**: `engine.py` kini menurunkan batas SL minimum khusus mode **Forex MT5** dari `0.35%` menjadi **`0.10%`** (membuat target & stop jauh lebih proporsional pada pasangan Forex & XAUUSD), sementara mode Spot & Futures menjaga floor `0.35%`. Buffer data M1 diperbesar ke `1440 bar` (24 jam).

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'macd_div':
def macd_divergence(s):
    """Deteksi divergensi MACD vs harga dengan dua jendela terpisah (disjoint)."""
    i = s.i
    if i < 30:
        return 0.0
    px_low_prev = float(s.l[i - 30:i - 14].min())
    px_low_now = float(s.l[i - 14:i + 1].min())
    macd_low_prev = float(s.macd[i - 30:i - 14].min())
    macd_low_now = float(s.macd[i - 14:i + 1].min())
    px_hi_prev = float(s.h[i - 30:i - 14].max())
    px_hi_now = float(s.h[i - 14:i + 1].max())
    macd_hi_prev = float(s.macd[i - 30:i - 14].max())
    macd_hi_now = float(s.macd[i - 14:i + 1].max())
    if px_low_now < px_low_prev and macd_low_now > macd_low_prev and s.c[i] > s.ema9[i]:
        return 0.65
    if px_hi_now > px_hi_prev and macd_hi_now < macd_hi_prev and s.c[i] < s.ema9[i]:
        return -0.65
    return 0.0
```
