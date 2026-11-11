# Spesifikasi Strategi #53: Wick Rejection (`wicks_reject`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **Wick Rejection**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#53` · `wicks_reject` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Order flow** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (1-Menit Bar Closed via `BarRing`) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 2.0`** | Otomatis berdasarkan cluster `Order flow` |
| **Leverage Default** | **`15x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.35\% \times \text{Harga})$ | Floor proteksi minimum 0.35% di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Mendeteksi penolakan sumbu panjang (> 1.8x panjang body candle) terhadap garis EMA21.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. Jika $(H_i - C_i) > 1.8 \cdot |C_i - O_i|$ dan $H_i > \text{EMA}_{21}$: return **`+0.6`**
2. Jika $(C_i - L_i) > 1.8 \cdot |C_i - O_i|$ dan $L_i < \text{EMA}_{21}$: return **`-0.6`**

### Visualisasi Alur Sinyal (Diagram Logika):
```text
       |  (Sumbu Atas Panjang > 1.8x Body -> Shooting Star Reject EMA21)
     [===]  ===> KODE MALAH ENTRY BUY (+0.6) BUKAN SELL!
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
   - $\text{TPDist} = 2.0 \times \text{StopDist}$
   - Jika muncul sinyal berlawanan arah (`pos.side != new_side`), posisi lama langsung ditutup (*reverse signal exit*) sebelum posisi baru dibuka.

---

## 5. Audit Risiko, Temuan Bug & Titik Lemah (*CRITICAL AUDIT*)

Hasil pemeriksaan langsung terhadap kode sumber `server/strategies.py`, `server/engine.py`, dan `server/forex_feed.py` menemukan catatan audit spesifik berikut untuk strategi ini:

* **🚨 CRITICAL BUG (Sinyal Terbalik 100% / Inverted!)**: Lihat baris 1188:
   - `(H - C)` adalah panjang **SUMBU ATAS** (penolakan resistance / *Bearish Shooting Star*). Seharusnya memicu **SELL (`-0.6`)**, tetapi kode mengembalikan **`+0.6` (BUY)**!
   - `(C - L)` adalah panjang **SUMBU BAWAH** (*Bullish Hammer*). Seharusnya memicu **BUY**, tetapi kode mengembalikan **`-0.6` (SELL)**!
   - Ditambah lagi jika candle merah (`c < o`), `(h - c)` menghitung sumbu atas + body, bukan sumbu atas murni `h - max(o, c)`!
* **⚠️ Catatan Umum Mesin M1 (`0.35% Minimum SL Floor`)**: Karena sinyal dievaluasi pada bar **1-menit (`M1`)**, sedangkan `engine.py` memaksa jarak Stop Loss minimal `0.35%` (~143 pips pada XAUUSD atau ~39 pips pada EURUSD), strategi jangka pendek M1 harus menahan fluktuasi lebar yang kerap tidak sebanding dengan target scalping-nya.

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'wicks_reject':
("wicks_reject", "Wick Rejection", "Order flow", lambda s: (0.6 if (s.h[s.i] - s.c[s.i]) > 1.8 * abs(s.c[s.i] - s.o[s.i] + 1e-12) and s.h[s.i] > s.ema21[s.i] else (-0.6 if (s.c[s.i] - s.l[s.i]) > 1.8 * abs(s.c[s.i] - s.o[s.i] + 1e-12) and s.l[s.i] < s.ema21[s.i] else 0.0))),
```
