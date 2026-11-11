# Spesifikasi Strategi #1: ICT Momentum (`ict_momentum`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **ICT Momentum**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#1` · `ict_momentum` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **ICT** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (1-Menit Bar Closed via `BarRing`) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.8`** | Otomatis berdasarkan cluster `ICT` |
| **Leverage Default** | **`15x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.35\% \times \text{Harga})$ | Floor proteksi minimum 0.35% di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Mengidentifikasi candle impulsif institusional (displacement bar) dengan body >= 1.6 ATR, lalu menunggu koreksi ke level 50% (equilibrium) body tersebut untuk entry searah tren.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. $|C_{i-1} - O_{i-1}| \ge 1.6 \times \text{ATR}_{14}$
2. $\text{Mid} = \frac{O_{i-1} + C_{i-1}}{2}$
3. **BUY**: $C_{i-1} > O_{i-1}$ dan $0.998 \cdot \text{Mid} \le C_i \le 1.002 \cdot \text{Mid}$ dan $C_i < \text{EMA}_9$
4. **SELL**: $C_{i-1} < O_{i-1}$ dan $0.998 \cdot \text{Mid} \le C_i \le 1.002 \cdot \text{Mid}$ dan $C_i > \text{EMA}_9$

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  [Candle Impulsif i-1]  =====>  [Pullback i ke 50% Midpoint]
  Open ------------+             Retest 0.998*Mid .. 1.002*Mid
                   |             + Filter c < EMA9 (Bull) / c > EMA9 (Bear)
  Mid (50%) -------+ <=========  ENTRY DI SINI
                   |
  Close -----------+
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

* **⚠️ Konflik Logika `c < EMA9` (Bullish)**: Setelah candle hijau impulsif besar (`>= 1.6 ATR`), EMA9 ikut naik tajam, namun sering kali saat pullback ke 50% midpoint harga masih di atas EMA9 atau jika sudah tembus di bawah EMA9 justru menandakan momentum gagal.
* **⚠️ Jendela Lookback Terlalu Sempit (`i - 1`)**: Hanya memeriksa 1 candle tepat sebelumnya (`i - 1`). Jika retest ke 50% terjadi pada candle ke-2 atau ke-3 setelah impuls, Order Block langsung diabaikan.
* **⚠️ Toleransi Persentase Tetap (±0.2%)**: Angka `0.998..1.002` tidak menyesuaikan volatilitas pair (pada XAUUSD 0.2% = ~$8, sedangkan pada EURUSD 0.2% = ~22 pips).
* **⚠️ Catatan Umum Mesin M1 (`0.35% Minimum SL Floor`)**: Karena sinyal dievaluasi pada bar **1-menit (`M1`)**, sedangkan `engine.py` memaksa jarak Stop Loss minimal `0.35%` (~143 pips pada XAUUSD atau ~39 pips pada EURUSD), strategi jangka pendek M1 harus menahan fluktuasi lebar yang kerap tidak sebanding dengan target scalping-nya.

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'ict_momentum':
def order_block(s):
    """Order block: candle impulsif jauh di luar ATR, lalu harga kembali ke 50%-nya."""
    i = s.i
    if i < 5:
        return 0.0
    atr = s.atr14[i]
    if not _ok(atr) or atr <= 0:
        return 0.0
    body = s.c[i - 1] - s.o[i - 1]
    c = s.c[i]
    if abs(body) < 1.6 * atr:
        return 0.0
    if body > 0:
        mid = (s.o[i - 1] + s.c[i - 1]) / 2
        if mid * 0.998 <= c <= mid * 1.002 and c < s.ema9[i]:
            return 0.7
    else:
        mid = (s.o[i - 1] + s.c[i - 1]) / 2
        if mid * 0.998 <= c <= mid * 1.002 and c > s.ema9[i]:
            return -0.7
    return 0.0
```
