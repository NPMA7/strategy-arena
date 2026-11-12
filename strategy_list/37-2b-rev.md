# Spesifikasi Strategi #37: 2B Close Reversal (`2b_rev`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **2B Close Reversal**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#37` · `2b_rev` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Price action** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (`BarRing` kapasitas 1440 bar / 24 jam) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.8`** | Otomatis berdasarkan cluster `Price action` |
| **Leverage Default** | **`10x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.10\% \text{ Forex} / 0.35\% \text{ Crypto})$ | Floor proteksi adaptif di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Implementasi sejati pola **Victor Sperandeo 2B Reversal**: mendeteksi ketika bar sebelumnya (`i-1`) sempat mencetak breakout di atas/bawah 20-bar ekstrem (jebakan likuiditas), lalu candle `i` berbalik masuk kembali menembus level breakout tersebut dan ditutup di bawah `L[i-1]` (atau di atas `H[i-1]`).

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. Hitung $\text{HH}_{20} = \max(H_{i-21..i-2})$ dan $\text{LL}_{20} = \min(L_{i-21..i-2})$.
2. **SELL (-0.75)**: $H_{i-1} > \text{HH}_{20}$ dan $C_i < \text{HH}_{20}$ dan $C_i < L_{i-1}$ dan $C_i < O_i$.
3. **BUY (+0.75)**: $L_{i-1} < \text{LL}_{20}$ dan $C_i > \text{LL}_{20}$ dan $C_i > H_{i-1}$ dan $C_i > O_i$.

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  Bar [i-1] Sweep > HH20 (False Break) ===> Bar [i] Close < HH20 & < Low[i-1] ===> SELL (-0.75)
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

* **✅ FIXED (Deduplikasi Dari #55 `price_action_2b` & Rename Ke `2B Close Reversal`)**: Bug lama menyebabkan #37 dan #55 memiliki nama dan fungsi identik. Kini #37 menjalankan `two_b_close_reversal` dengan syarat false-break 20-bar yang valid.
* **ℹ️ Pembaruan Mesin M1 (`0.10% Forex SL Floor` & `1440-Bar History`)**: `engine.py` kini menurunkan batas SL minimum khusus mode **Forex MT5** dari `0.35%` menjadi **`0.10%`** (membuat target & stop jauh lebih proporsional pada pasangan Forex & XAUUSD), sementara mode Spot & Futures menjaga floor `0.35%`. Buffer data M1 diperbesar ke `1440 bar` (24 jam).

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk '2b_rev':
def two_b_close_reversal(s):
    """Sperandeo 2B Reversal: false breakout 20-bar high/low diikuti close konfirmasi ke dalam range."""
    i = s.i
    if i < 22:
        return 0.0
    hh = float(s.h[i - 21:i - 1].max())
    ll = float(s.l[i - 21:i - 1].min())
    c, o = s.c[i], s.o[i]
    if s.h[i - 1] > hh and c < hh and c < s.l[i - 1] and c < o:
        return -0.75
    if s.l[i - 1] < ll and c > ll and c > s.h[i - 1] and c > o:
        return 0.75
    return 0.0
```
