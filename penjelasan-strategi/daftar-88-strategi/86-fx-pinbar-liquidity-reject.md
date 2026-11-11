# Spesifikasi Strategi #86: Pin Bar Liquidity Rejection (`fx_pinbar_liquidity_reject`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **Pin Bar Liquidity Rejection**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#86` · `fx_pinbar_liquidity_reject` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Price action** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (1-Menit Bar Closed via `BarRing`) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.8`** | Otomatis berdasarkan cluster `Price action` |
| **Leverage Default** | **`1x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.35\% \times \text{Harga})$ | Floor proteksi minimum 0.35% di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Mendeteksi candlestick Pin Bar (sumbu >= 60%, body <= 32%) yang menyentuh serta menolak garis EMA21.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. **BUY**: $\text{LowerWick}/\text{Rng} \ge 0.60$, $\text{Body}/\text{Rng} \le 0.32$, $L_i < \text{EMA}_{21} \le C_i \cdot 1.001$
2. **SELL**: $\text{UpperWick}/\text{Rng} \ge 0.60$, $\text{Body}/\text{Rng} \le 0.32$, $H_i > \text{EMA}_{21} \ge C_i \cdot 0.999$

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  Pin Bar Ekor Panjang >= 60% Menyentuh Garis EMA21 ===> ENTRY
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

* **✅ Rumus Pin Bar Benar (Tidak Terbalik seperti `wicks_reject`!)**. Catatan: Syarat sumbu >= 60% sekaligus menyentuh EMA21 di candle yang sama cukup selektif sehingga menghasilkan sinyal yang jarang namun berkualitas.
* **⚠️ Catatan Umum Mesin M1 (`0.35% Minimum SL Floor`)**: Karena sinyal dievaluasi pada bar **1-menit (`M1`)**, sedangkan `engine.py` memaksa jarak Stop Loss minimal `0.35%` (~143 pips pada XAUUSD atau ~39 pips pada EURUSD), strategi jangka pendek M1 harus menahan fluktuasi lebar yang kerap tidak sebanding dengan target scalping-nya.

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'fx_pinbar_liquidity_reject':
def fx_pinbar_liquidity_reject(s):
    """Pin Bar Rejection of Dynamic S/R (EMA21/50)."""
    c, o, h, l, e21 = s.c[s.i], s.o[s.i], s.h[s.i], s.l[s.i], s.ema21[s.i]
    if not _ok(c, o, h, l, e21):
        return 0.0
    rng = max(h - l, 1e-9)
    body = abs(c - o)
    # Bullish Hammer/Pin: lower wick >= 60% of candle range, body <= 30%
    if (min(o, c) - l) / rng >= 0.60 and body / rng <= 0.32:
        if l < e21 and c >= e21 * 0.999:
            return 0.80
    # Bearish Shooting Star/Pin: upper wick >= 60% of candle range, body <= 30%
    if (h - max(o, c)) / rng >= 0.60 and body / rng <= 0.32:
        if h > e21 and c <= e21 * 1.001:
            return -0.80
    return 0.0
```
