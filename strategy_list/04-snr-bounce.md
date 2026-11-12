# Spesifikasi Strategi #4: Support Resistance Bounce (`snr_bounce`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **Support Resistance Bounce**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#4` · `snr_bounce` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Price action** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (`BarRing` kapasitas 1440 bar / 24 jam) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.8`** | Otomatis berdasarkan cluster `Price action` |
| **Leverage Default** | **`10x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.10\% \text{ Forex} / 0.35\% \text{ Crypto})$ | Floor proteksi adaptif di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Pantulan Support & Resistance murni menggunakan Classic Pivot (P, R1, S1) dari bar sebelumnya: membeli saat harga menguji/menyentuh zona S1 namun menolak turun (ditutup hijau di atas S1), dan menjual saat harga menguji R1 lalu ditolak turun (ditutup merah di bawah R1).

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. $P = (H_{i-1} + L_{i-1} + C_{i-1}) / 3$, $\;R_1 = 2P - L_{i-1}$, $\;S_1 = 2P - H_{i-1}$.
2. **BUY (+0.60)**: $(L_i \le S_1 \text{ atau } C_{i-1} \le S_1)$ dan $C_i > S_1$ dan $C_i > O_i$.
3. **SELL (-0.60)**: $(H_i \ge R_1 \text{ atau } C_{i-1} \ge R_1)$ dan $C_i < R_1$ dan $C_i < O_i$.

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  R1 ---/\--- Reject (Close < R1, Bear) => SELL (-0.60)
  P  -------- Pivot
  S1 ---\/--- Bounce (Close > S1, Bull) => BUY  (+0.60)
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

* **✅ FIXED (Bug Logika Reversal Terbalik Diperbaiki)**: Logika lama keliru entry BUY ketika `c < s1` (menangkap breakout jatuh). Kini `pivot_bounce` mewajibkan konfirmasi harga kembali memantul melewati S1/R1 dengan warna candle penolakan yang searah.
* **⚠️ Catatan Pivot M1**: Level S1/R1 masih dihitung dari bar M1 `i-1`, sehingga cocok untuk mikro-rebound cepat.
* **ℹ️ Pembaruan Mesin M1 (`0.10% Forex SL Floor` & `1440-Bar History`)**: `engine.py` kini menurunkan batas SL minimum khusus mode **Forex MT5** dari `0.35%` menjadi **`0.10%`** (membuat target & stop jauh lebih proporsional pada pasangan Forex & XAUUSD), sementara mode Spot & Futures menjaga floor `0.35%`. Buffer data M1 diperbesar ke `1440 bar` (24 jam).

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'snr_bounce':
def pivot_bounce(s):
    """Support/Resistance Bounce: memantul naik dari S1 atau ditolak turun dari R1."""
    i = s.i
    piv = (s.h[i - 1] + s.l[i - 1] + s.c[i - 1]) / 3
    r1 = 2 * piv - s.l[i - 1]
    s1 = 2 * piv - s.h[i - 1]
    c = s.c[i]
    if (s.l[i] <= s1 or s.c[i - 1] <= s1) and c > s1 and c > s.o[i]:
        return 0.6
    if (s.h[i] >= r1 or s.c[i - 1] >= r1) and c < r1 and c < s.o[i]:
        return -0.6
    return 0.0
```
