# Spesifikasi Strategi #60: New York Fixing Reversal (`fx_ny_reversal`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **New York Fixing Reversal**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#60` · `fx_ny_reversal` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Mean reversion** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (1-Menit Bar Closed via `BarRing`) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.5`** | Otomatis berdasarkan cluster `Mean reversion` |
| **Leverage Default** | **`1x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.35\% \times \text{Harga})$ | Floor proteksi minimum 0.35% di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

New York Fixing Reversal: melakukan fade deviasi ekstrem (> 0.3 ATR di luar Bollinger Band + RSI ekstrem) pada jam penutupan London / NY Fixing (15:00–17:59 UTC).

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. Jam UTC $\in \{15, 16, 17\}$
2. **SELL**: $C_i > \text{BB}_{upper} + 0.3\cdot\text{ATR}_{14}$ dan $\text{RSI}_{14} > 72$
3. **BUY**: $C_i < \text{BB}_{lower} - 0.3\cdot\text{ATR}_{14}$ dan $\text{RSI}_{14} < 28$

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  [15-17 UTC] + Harga Melampaui BB Band +- 0.3 ATR + RSI Ekstrem ===> REVERSAL
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
   - $\text{TPDist} = 1.5 \times \text{StopDist}$
   - Jika muncul sinyal berlawanan arah (`pos.side != new_side`), posisi lama langsung ditutup (*reverse signal exit*) sebelum posisi baru dibuka.

---

## 5. Audit Risiko, Temuan Bug & Titik Lemah (*CRITICAL AUDIT*)

Hasil pemeriksaan langsung terhadap kode sumber `server/strategies.py`, `server/engine.py`, dan `server/forex_feed.py` menemukan catatan audit spesifik berikut untuk strategi ini:

* **✅ Cukup Efektif (+0.88% / #21 di Leaderboard)**. Catatan: Saat terjadi pengumuman FOMC/The Fed pada pukul 18:00–19:00 UTC atau pidato pukul 15:00 UTC, volatilitas dapat menembus band jauh lebih dari 0.3 ATR.
* **⚠️ Catatan Umum Mesin M1 (`0.35% Minimum SL Floor`)**: Karena sinyal dievaluasi pada bar **1-menit (`M1`)**, sedangkan `engine.py` memaksa jarak Stop Loss minimal `0.35%` (~143 pips pada XAUUSD atau ~39 pips pada EURUSD), strategi jangka pendek M1 harus menahan fluktuasi lebar yang kerap tidak sebanding dengan target scalping-nya.

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'fx_ny_reversal':
def fx_ny_reversal(s):
    """New York Institutional Fixing Reversal: Jam 15:00 - 17:00 UTC."""
    hour = int((s.ts[s.i] // 3600000) % 24)
    if hour not in (15, 16, 17):
        return 0.0
    c, bu, bl, atr, rsi = s.c[s.i], s.bb_u[s.i], s.bb_l[s.i], s.atr14[s.i], s.rsi14[s.i]
    if not _ok(c, bu, bl, atr, rsi):
        return 0.0
    if c > bu + 0.3 * atr and rsi > 72:
        return -0.8
    if c < bl - 0.3 * atr and rsi < 28:
        return 0.8
    return 0.0
```
