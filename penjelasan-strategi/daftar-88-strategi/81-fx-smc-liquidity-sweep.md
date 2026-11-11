# Spesifikasi Strategi #81: SMC Liquidity Sweep & BOS (`fx_smc_liquidity_sweep`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **SMC Liquidity Sweep & BOS**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#81` · `fx_smc_liquidity_sweep` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Struktur** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (1-Menit Bar Closed via `BarRing`) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.8`** | Otomatis berdasarkan cluster `Struktur` |
| **Leverage Default** | **`1x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.35\% \times \text{Harga})$ | Floor proteksi minimum 0.35% di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Mencari sapuan likuiditas: harga menembus ke bawah Low 20-bar tetapi ditutup kembali di atasnya dengan sumbu bawah rejection >= 45% dari rentang candle.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. **BUY**: $L_i < \text{LL}_{20}[i-1]$ dan $C_i > \text{LL}_{20}[i-1]$ dan $\frac{\min(O_i, C_i) - L_i}{\text{Rng}} \ge 0.45$
2. **SELL**: Kebalikannya (sumbu atas >= 45% menolak $\text{HH}_{20}[i-1]$).

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  LL20  ------\  /------  Close kembali di atas LL20 + Wick Bawah >= 45% => BUY
               \/ (Sapuan)
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

* **✅ Logika Liquidity Sweep yang Sangat Valid**. Catatan: Syarat wick 45% pada M1 agak ketat pada pair yang bergerak bertahap sehingga frekuensi entry rendah.
* **⚠️ Catatan Umum Mesin M1 (`0.35% Minimum SL Floor`)**: Karena sinyal dievaluasi pada bar **1-menit (`M1`)**, sedangkan `engine.py` memaksa jarak Stop Loss minimal `0.35%` (~143 pips pada XAUUSD atau ~39 pips pada EURUSD), strategi jangka pendek M1 harus menahan fluktuasi lebar yang kerap tidak sebanding dengan target scalping-nya.

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'fx_smc_liquidity_sweep':
def fx_smc_liquidity_sweep(s):
    """SMC Liquidity Sweep & Market Structure Shift (MSS)."""
    c, o, h, l, hh, ll = s.c[s.i], s.o[s.i], s.h[s.i], s.l[s.i], s.hh20[s.i - 1], s.ll20[s.i - 1]
    if not _ok(c, o, h, l, hh, ll):
        return 0.0
    rng = max(h - l, 1e-9)
    # Sellside Liquidity Sweep: price sweeps below 20-bar low, but closes back above with lower wick >= 50%
    if l < ll and c > ll and (min(o, c) - l) / rng >= 0.45:
        return 0.85
    # Buyside Liquidity Sweep: price sweeps above 20-bar high, but closes back below with upper wick >= 50%
    if h > hh and c < hh and (h - max(o, c)) / rng >= 0.45:
        return -0.85
    return 0.0
```
