# Spesifikasi Strategi #85: Three Line Strike Pattern (`fx_three_line_strike`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **Three Line Strike Pattern**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#85` · `fx_three_line_strike` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Price action** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (1-Menit Bar Closed via `BarRing`) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.8`** | Otomatis berdasarkan cluster `Price action` |
| **Leverage Default** | **`1x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.35\% \times \text{Harga})$ | Floor proteksi minimum 0.35% di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Pola pembalikan langka 4-bar: 3 candle berurutan dengan close makin menurun, lalu disapu habis oleh 1 candle hijau ke-4 yang dibuka di bawah `c1` dan ditutup di atas `o3`.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. **BUY**: $C_3 < O_3, C_2 < O_2, C_1 < O_1, C_1 < C_2 < C_3$, lalu $C_0 > O_0, O_0 \le C_1, C_0 > O_3$.

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  3 Candle Merah Turun Beruntun -> 1 Candle Hijau Raksasa Menelan Semuanya => BUY
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

* **⚠️ Syarat Nyaris Mustahil di Timeframe 1-Menit (`0.00%` di UI)**: Mengharuskan satu candle berdurasi 60 detik menelan rentang penuh 3 candle sebelumnya sekaligus memiliki kondisi pembukaan `o0 <= c1` hampir tidak pernah terjadi di kondisi pasar wajar.
* **⚠️ Catatan Umum Mesin M1 (`0.35% Minimum SL Floor`)**: Karena sinyal dievaluasi pada bar **1-menit (`M1`)**, sedangkan `engine.py` memaksa jarak Stop Loss minimal `0.35%` (~143 pips pada XAUUSD atau ~39 pips pada EURUSD), strategi jangka pendek M1 harus menahan fluktuasi lebar yang kerap tidak sebanding dengan target scalping-nya.

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'fx_three_line_strike':
def fx_three_line_strike(s):
    """Three Line Strike Price Action Reversal."""
    if s.i < 4:
        return 0.0
    c0, o0 = s.c[s.i], s.o[s.i]
    c1, o1 = s.c[s.i - 1], s.o[s.i - 1]
    c2, o2 = s.c[s.i - 2], s.o[s.i - 2]
    c3, o3 = s.c[s.i - 3], s.o[s.i - 3]
    if not _ok(c0, o0, c1, o1, c2, o2, c3, o3):
        return 0.0
    # Bullish Strike: 3 consecutive bear bars wiped out by 1 powerful bull candle
    if c3 < o3 and c2 < o2 and c1 < o1 and c1 < c2 < c3:
        if c0 > o0 and c0 > o3 and o0 <= c1:
            return 0.85
    # Bearish Strike: 3 consecutive bull bars wiped out by 1 powerful bear candle
    if c3 > o3 and c2 > o2 and c1 > o1 and c1 > c2 > c3:
        if c0 < o0 and c0 < o3 and o0 >= c1:
            return -0.85
    return 0.0
```
