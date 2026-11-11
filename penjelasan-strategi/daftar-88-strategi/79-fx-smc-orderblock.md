# Spesifikasi Strategi #79: SMC Order Block Mitigation (`fx_smc_orderblock`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **SMC Order Block Mitigation**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#79` · `fx_smc_orderblock` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **ICT** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (1-Menit Bar Closed via `BarRing`) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.8`** | Otomatis berdasarkan cluster `ICT` |
| **Leverage Default** | **`1x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.35\% \times \text{Harga})$ | Floor proteksi minimum 0.35% di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Memindai 2 hingga 10 candle ke belakang untuk mencari candle berlawanan terakhir sebelum gelombang pergerakan kuat (`> 1.1 ATR`), lalu entry saat candle saat ini masuk ke area Order Block dan tutup searah.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. Loop $k \in [i-2 .. i-10]$ mencari candle merah ($C_k < O_k$) diikuti lonjakan $(C_{k+1} - C_k) > 1.1\cdot\text{ATR}_{14}$.
2. **BUY**: Candle $i$ menyentuh $[L_k, H_k]$ (`l <= ob_high and c >= ob_low`) dan $C_i > O_i$.

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  OB Bar [k] (Merah) ===> Displacement [k+1] ===> Harga Pulang ke [L_k..H_k] + Close Hijau => BUY
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

* **✅ Implementasi SMC Sejati Yang Bersih!** Catatan audit: `break` di dalam loop langsung menghentikan pencarian begitu menemukan satu OB terdekat, meski OB tersebut mungkin sudah pernah dimitigasi atau ditembus pada bar-bar di antara `k+2` sampai `i-1`. Perlu pengecekan apakah OB masih *unmitigated* (fresh).
* **⚠️ Catatan Umum Mesin M1 (`0.35% Minimum SL Floor`)**: Karena sinyal dievaluasi pada bar **1-menit (`M1`)**, sedangkan `engine.py` memaksa jarak Stop Loss minimal `0.35%` (~143 pips pada XAUUSD atau ~39 pips pada EURUSD), strategi jangka pendek M1 harus menahan fluktuasi lebar yang kerap tidak sebanding dengan target scalping-nya.

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'fx_smc_orderblock':
def fx_smc_orderblock(s):
    """Institutional Order Block Mitigation (SMC)."""
    if s.i < 15:
        return 0.0
    c, o, h, l, atr = s.c[s.i], s.o[s.i], s.h[s.i], s.l[s.i], s.atr14[s.i]
    if not _ok(c, o, h, l, atr) or atr <= 0:
        return 0.0
    # Bullish OB: last down candle before displacement wave up, retested by current candle
    for k in range(s.i - 2, max(s.i - 10, 1), -1):
        if s.c[k] < s.o[k] and (s.c[k + 1] - s.c[k]) > 1.1 * atr:
            ob_high, ob_low = s.h[k], s.l[k]
            if l <= ob_high and c >= ob_low and c > o:
                return 0.80
            break
    # Bearish OB: last up candle before displacement wave down, retested by current candle
    for k in range(s.i - 2, max(s.i - 10, 1), -1):
        if s.c[k] > s.o[k] and (s.c[k] - s.c[k + 1]) > 1.1 * atr:
            ob_high, ob_low = s.h[k], s.l[k]
            if h >= ob_low and c <= ob_high and c < o:
                return -0.80
            break
    return 0.0
```
