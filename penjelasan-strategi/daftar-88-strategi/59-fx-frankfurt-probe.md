# Spesifikasi Strategi #59: Frankfurt Liquidity Probe (`fx_frankfurt_probe`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **Frankfurt Liquidity Probe**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#59` · `fx_frankfurt_probe` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Order flow** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (1-Menit Bar Closed via `BarRing`) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 2.0`** | Otomatis berdasarkan cluster `Order flow` |
| **Leverage Default** | **`1x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.35\% \times \text{Harga})$ | Floor proteksi minimum 0.35% di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Frankfurt Liquidity Probe: aktif khusus jam 06:00–06:59 UTC (pembukaan pasar Frankfurt), mencari sapuan 10-bar ekstrem yang langsung ditutup melewati rata-rata BB Middle.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. Jam UTC $== 6$
2. **BUY**: $L_i < \text{LL}_{10}[i-1]$ dan $C_i > \text{BB}_{mid}$
3. **SELL**: $H_i > \text{HH}_{10}[i-1]$ dan $C_i < \text{BB}_{mid}$

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  [Jam 06 UTC] -> Sapu LL10 tapi Close > SMA20 dalam 1 candle ===> BUY
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

* **⚠️ Terlalu Jarang Terpenuhi (0.00% / #40 di Leaderboard)**: Dalam rentang waktu hanya 1 jam per hari, mengharuskan sebuah bar M1 menembus LL10 lalu berbalik menutup di atas SMA20 dalam waktu 60 detik sangat ekstrem dan hampir tak pernah terjadi.
* **⚠️ Catatan Umum Mesin M1 (`0.35% Minimum SL Floor`)**: Karena sinyal dievaluasi pada bar **1-menit (`M1`)**, sedangkan `engine.py` memaksa jarak Stop Loss minimal `0.35%` (~143 pips pada XAUUSD atau ~39 pips pada EURUSD), strategi jangka pendek M1 harus menahan fluktuasi lebar yang kerap tidak sebanding dengan target scalping-nya.

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'fx_frankfurt_probe':
def fx_frankfurt_probe(s):
    """Frankfurt Liquidity Probe: Menjebak likuiditas awal jam 06:00 UTC."""
    hour = int((s.ts[s.i] // 3600000) % 24)
    if hour != 6:
        return 0.0
    c, l, h, ll, hh = s.c[s.i], s.l[s.i], s.h[s.i], s.ll10[s.i - 1], s.hh10[s.i - 1]
    if not _ok(c, l, h, ll, hh):
        return 0.0
    if l < ll and c > s.bb_m[s.i]:
        return 0.75
    if h > hh and c < s.bb_m[s.i]:
        return -0.75
    return 0.0
```
