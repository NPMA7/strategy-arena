# Spesifikasi Strategi #47: Range Expansion Fade (`tr_break`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **Range Expansion Fade**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#47` · `tr_break` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Volatility** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (`BarRing` kapasitas 1440 bar / 24 jam) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.8`** | Otomatis berdasarkan cluster `Volatility` |
| **Leverage Default** | **`15x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.10\% \text{ Forex} / 0.35\% \text{ Crypto})$ | Floor proteksi adaptif di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Range Expansion Fade sejati: mendeteksi bar dengan True Range ekstrem (`>= 2.4x ATR14`) lalu mengambil posisi berlawanan arah (*mean reversion fading*) karena lonjakan satu bar melebihi dua kali volatilitas normal cenderung mengalami kelelahan (*exhaustion*).

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. $\text{TR}_i = \max(H_i - L_i, \; |H_i - C_{i-1}|, \; |L_i - C_{i-1}|)$.
2. Syarat Ekspansi: $\text{TR}_i \ge 2.4 \times \text{ATR}_{14}$.
3. **SELL (-0.80)**: Jika bar ekstrem ditutup hijau ($C_i > O_i$) -> fade lonjakan naik.
4. **BUY (+0.80)**: Jika bar ekstrem ditutup merah ($C_i < O_i$) -> fade lonjakan turun.

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  [Bar Ekstrem TR >= 2.4 ATR Hijau] ===> FADE SELL (-0.80)
  [Bar Ekstrem TR >= 2.4 ATR Merah] ===> FADE BUY  (+0.80)
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

* **✅ FIXED (Bug Sinyal Terbalik Diperbaiki)**: Kesalahan tanda lama (`return -1 if c < o else 1`) telah dibalik ke arah fade yang semestinya (`-0.8` untuk candle ekstrem hijau, `+0.8` untuk candle ekstrem merah).
* **ℹ️ Pembaruan Mesin M1 (`0.10% Forex SL Floor` & `1440-Bar History`)**: `engine.py` kini menurunkan batas SL minimum khusus mode **Forex MT5** dari `0.35%` menjadi **`0.10%`** (membuat target & stop jauh lebih proporsional pada pasangan Forex & XAUUSD), sementara mode Spot & Futures menjaga floor `0.35%`. Buffer data M1 diperbesar ke `1440 bar` (24 jam).

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'tr_break':
def tr_break(s):
    """True Range expansion: lawan impuls ekstrem sesaat."""
    i = s.i
    atr = s.atr14[i]
    if not _ok(atr) or atr <= 0:
        return 0.0
    tr = max(s.h[i] - s.l[i], abs(s.h[i] - s.c[i - 1]), abs(s.l[i] - s.c[i - 1]))
    if tr < 2.4 * atr:
        return 0.0
    if s.c[i] > s.o[i]:
        return -0.8
    if s.c[i] < s.o[i]:
        return 0.8
    return 0.0
```
