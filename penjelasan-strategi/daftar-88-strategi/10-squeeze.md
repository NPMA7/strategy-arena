# Spesifikasi Strategi #10: Squeeze Release (`squeeze`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **Squeeze Release**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#10` · `squeeze` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Volatility** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (`BarRing` kapasitas 1440 bar / 24 jam) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.8`** | Otomatis berdasarkan cluster `Volatility` |
| **Leverage Default** | **`15x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.10\% \text{ Forex} / 0.35\% \text{ Crypto})$ | Floor proteksi adaptif di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Mengidentifikasi kompresi volatilitas saat lebar Bollinger Bands menyempit di bawah 75% rata-rata 100 bar terakhir, lalu entry saat harga menembus band.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. $\text{Width}_t = \text{BB}_{upper} - \text{BB}_{lower}$
2. $\text{Syarat Kompresi}$: $\text{Width}_i \le 0.75 \times \text{Mean}(\text{Width}_{i-99..i-1})$
3. **BUY**: Kompresi terpenuhi + $C_i > \text{BB}_{upper}[i]$ dan $C_{i-1} \le \text{BB}_{upper}[i-1]$

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  ---=====[ Fase Squeeze (Width <= 75% Avg) ]=====---
                                                    \--> Breakout Upper = BUY
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

* **⚠️ Konflik Matematis Ringan**: Ketika harga langsung breakout keras melewati `BB_upper` pada bar `i`, standar deviasi 20-bar ikut melompat naik sehingga `Width_i` ikut melebar dan terkadang langsung menggugurkan syarat `Width_i <= 0.75 * avg` di bar breakout itu sendiri.
* **⚠️ Rentan Head-Fake**: Arah tembusan pertama keluar dari fase squeeze sering menjebak sebelum harga berbalik tajam.
* **ℹ️ Pembaruan Mesin M1 (`0.10% Forex SL Floor` & `1440-Bar History`)**: `engine.py` kini menurunkan batas SL minimum khusus mode **Forex MT5** dari `0.35%` menjadi **`0.10%`** (membuat target & stop jauh lebih proporsional pada pasangan Forex & XAUUSD), sementara mode Spot & Futures menjaga floor `0.35%`. Buffer data M1 diperbesar ke `1440 bar` (24 jam).

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'squeeze':
def squeeze(s):
    i = s.i
    if i < 100 or not _ok(s.bb_u[i], s.bb_l[i]):
        return 0.0
    widths = s.bb_u[i - 99:i + 1] - s.bb_l[i - 99:i + 1]
    avg = float(widths[:-1].mean())
    if avg <= 0 or (s.bb_u[i] - s.bb_l[i]) > avg * 0.75:
        return 0.0
    if s.c[i] > s.bb_u[i] and s.c[i - 1] <= s.bb_u[i - 1]:
        return 0.85
    if s.c[i] < s.bb_l[i] and s.c[i - 1] >= s.bb_l[i - 1]:
        return -0.85
    return 0.0
```
