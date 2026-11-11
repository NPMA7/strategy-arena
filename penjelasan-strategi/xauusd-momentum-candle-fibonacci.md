# Spesifikasi Strategi: Momentum Candle Fibonacci Retest (MC-FIBO)

Dokumen ini memuat blueprint arsitektur logika dan spesifikasi algoritmik dari strategi **Momentum Candle Fibonacci Retest**. Dokumen ini diformat secara presisi agar dapat dibaca, dianalisis, dan dikembangkan lebih lanjut oleh agent AI (seperti Claude, atau GPT) serta diimplementasikan ke dalam bot trading / backend Strategy Arena.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Spesifikasi / Aturan | Keterangan |
| :--- | :--- | :--- |
| **Simbol Target** | `XAUUSD` (Spot Gold / Emas) | Strategi ini hanya aktif untuk pair XAUUSD |
| **Timeframe Eksekusi (LTF)** | `M15` (15-Menit) | Pembacaan momentum candle dan eksekusi entry |
| **Timeframe Konfirmasi (HTF)**| `M30` & `H1` | Filter arah tren & validasi momentum probabilitas tinggi |
| **Filter Sesi Waktu** | **Sesi Asia** & **Sesi New York** | Menghindari fase konsolidasi / whipsaw di luar likuiditas utama |
| **Model Eksekusi** | Limit Order / Retest Market Execution | Menunggu harga retest ke zona diskon Fibonacci |
| **Rasio Risk-to-Reward (R:R)**| **1 : 1.5** hingga **1 : 3.5** | Asimetris dengan Stop Loss ketat di origin momentum |

---

## 2. Multi-Timeframe High Probability Confirmation (HTF: H1 & M30)

Sebelum sistem mencari setup candle momentum di M15, sistem wajib melakukan validasi hirarki timeframe yang lebih tinggi untuk memastikan trading searah dengan institusi (*High-Probability Confluence*):

```
       [H1: Arah Dominan & Struktur Tren]
                       ↓
     [M30: Konfirmasi Kekuatan Momentum]
                       ↓
   [M15: Trigger Momentum Candle & Fibonacci Retest]
```

### A. Validasi Timeframe H1:
1. **Arah Tren & Dorongan**:
   - Untuk **Setup Sell (Bearish)**: Tren H1 harus jelas menunjukkan dorongan turun (misal: harga berada di bawah EMA 20/50 H1, atau candle H1 terakhir ditutup sebagai candle merah impulsif tanpa penolakan balik yang berarti).
   - Untuk **Setup Buy (Bullish)**: Tren H1 harus jelas menunjukkan dorongan naik (harga berada di atas EMA 20/50 H1, atau candle H1 terakhir ditutup sebagai candle hijau impulsif).
2. **Kondisi Tidak Valid (No Trade)**: Jika H1 sedang berada di area sideway sempit (*doji cluster*), setup M15 **dibatalkan**.

### B. Validasi Timeframe M30:
1. **Momentum Acceleration**:
   - Candle M30 terakhir atau 2 candle M30 terakhir wajib membentuk *Lower Low* dan *Lower High* (untuk Bearish) atau *Higher High* dan *Higher Low* (untuk Bullish).
   - Memastikan tidak ada pola divergence terbalik di M30 saat setup M15 terbentuk.

---

## 3. Karakteristik "Momentum Candle" di M15

Setup dipicu saat sebuah candle M15 selesai ditutup (*closed*) dengan karakteristik impulsif yang kuat:

1. **Rasio Body terhadap Range (Body Dominance)**:
   $$\text{Body Ratio} = \frac{|\text{Close} - \text{Open}|}{\text{High} - \text{Low}} \ge 0.65 \quad (65\%-75\%)$$
   - Body harus dominan, menandakan tekanan beli/jual yang tidak terlawan.
2. **Besaran Candle (Volatility Filter)**:
   $$\text{Range Candle} = (\text{High} - \text{Low}) \ge 1.5 \times \text{ATR}_{14}(M15)$$
   - Candle harus berukuran signifikan terhadap rata-rata volatilitas 14 periode terakhir.

---

## 4. Pemetaan Level Fibonacci (Anchoring Rules: Wick vs Body)

Sesuai aturan fleksibel: **"Jika ada sumbu/wick, tarik ke ujung wick; jika tidak ada wick (flat/marubozu), tarik ke body"**.

```
   (Bearish Setup)
   Level 1.000 ─────── [Open / High Wick jika ada]  <-- Stop Loss (SL)
     │
     ├── 0.786 ─────── Retest Zone 3 (Deep Discount)
     ├── 0.618 ─────── Golden Ratio
     ├── 0.500 ─────── Retest Zone 2 (Equilibrium)
     ├── 0.236 ─────── Retest Zone 1 (Shallow Retest)
     │
   Level 0.000 ─────── [Close / Low Wick jika ada]   <-- Take Profit 1 (TP1)
     │
   Level -0.270 ────── [Fibonacci Extension Target]  <-- Take Profit 2 (TP2 / Final)
```

### A. Aturan Anchoring Bearish (Sell Setup):
* **Level 1.000 (Origin / Pangkal Awal Momentum)**:
  - Jika ada *upper wick*, tarik tepat pada **High** candle.
  - Jika tidak ada *upper wick* (*flat open*), tarik pada harga **Open** candle.
* **Level 0.000 (Terminal / Titik Terjauh Dorongan)**:
  - Jika ada *lower wick*, tarik tepat pada **Low** candle.
  - Jika tidak ada *lower wick* (*flat close*), tarik pada harga **Close** candle.
* **Rentang Delta**: $\Delta = \text{Level}_{1.0} - \text{Level}_{0.0}$
* **Tingkatan Retest**:
  - $\text{Level}_{0.236} = \text{Level}_{0.0} + (0.236 \times \Delta)$
  - $\text{Level}_{0.500} = \text{Level}_{0.0} + (0.500 \times \Delta)$
  - $\text{Level}_{0.618} = \text{Level}_{0.0} + (0.618 \times \Delta)$
  - $\text{Level}_{0.786} = \text{Level}_{0.0} + (0.786 \times \Delta)$
* **Target Ekstensi TP2**:
  - $\text{Level}_{-0.270} = \text{Level}_{0.0} - (0.270 \times \Delta)$

### B. Aturan Anchoring Bullish (Buy Setup):
* **Level 1.000 (Origin Bawah)**: **Low** (jika ada wick) atau **Open** (jika flat).
* **Level 0.000 (Terminal Atas)**: **High** (jika ada wick) atau **Close** (jika flat).
* **Rentang Delta**: $\Delta = \text{Level}_{0.0} - \text{Level}_{1.0}$
* **Tingkatan Retest**:
  - $\text{Level}_{0.236} = \text{Level}_{0.0} - (0.236 \times \Delta)$
  - $\text{Level}_{0.500} = \text{Level}_{0.0} - (0.500 \times \Delta)$
  - $\text{Level}_{0.618} = \text{Level}_{0.0} - (0.618 \times \Delta)$
  - $\text{Level}_{0.786} = \text{Level}_{0.0} - (0.786 \times \Delta)$
* **Target Ekstensi TP2**:
  - $\text{Level}_{+1.270} = \text{Level}_{0.0} + (0.270 \times \Delta)$

---

## 5. Logika Eksekusi & Proteksi Risiko

### 1. Titik Entry (Retest Entry Trigger)
Setelah candle momentum M15 terbentuk dan ditutup, sistem menunggu candle berikutnya (maksimal dalam rentang 1-4 candle berikutnya) untuk melakukan *pullback/retest*:
* **Tipe Entry**:
  - **Limit Order Bertingkat**: Membagi lot menjadi 3 bagian pada level `0.236` (misal 20%), `0.500` (misal 40%), dan `0.786` (misal 40%).
  - **Single Retest Trigger**: Menunggu konfirmasi pantulan harga saat menyentuh zona `0.500 - 0.786`.
* **Invalidation / Pembatalan Setup**:
  - Jika harga langsung menembus melewati **Level 1.000** sebelum sinyal terekskusi, setup **gugur** dan seluruh pending order dibatalkan.
  - Jika harga sudah menembus langsung ke target -0.27 tanpa retest, setup **selesai / di-skip**.

### 2. Stop Loss (SL)
* Diletakkan di **Level 1.000** (High/Open candle momentum) + buffer spread sebesar 1.5 - 2.0 pips pada XAUUSD.

### 3. Take Profit (TP)
* **TP 1**: Pada **Level 0.000** (Low/Close candle momentum).
* **TP 2 (Target Penuh)**: Pada **Level -0.270** (Fibonacci Expansion).

---

## 6. Jendela Waktu Sesi Trading (Session Filters)

Trading hanya diperbolehkan pada jendela waktu likuiditas tinggi:
1. **Sesi Asia (Tokyo & Sydney)**:
   - Jam WIB: **07:00 – 13:00 WIB** (00:00 – 06:00 UTC).
2. **Sesi New York (US Session & Overlap London)**:
   - Jam WIB: **19:00 – 03:00 WIB** (12:00 – 20:00 UTC).
3. **Di luar kedua sesi ini**: Bot tidak melakukan scan atau membuka posisi baru (*Sleep / Audit Mode*).

---

## 7. Pseudocode Algoritmik untuk Pengembang (Opus / GPT / Astra)

```python
# ==============================================================================
# ALGORITHMIC SPECIFICATION: MC-FIBO (XAUUSD M15)
# ==============================================================================

def evaluate_mc_fibo_strategy(symbol, current_utc_hour, m15_bars, m30_bars, h1_bars):
    # 1. Filter Pair
    if symbol != "XAUUSD":
        return None

    # 2. Filter Sesi (Asia: 00-06 UTC, NY: 12-20 UTC)
    in_asia = (0 <= current_utc_hour < 6)
    in_ny = (12 <= current_utc_hour < 20)
    if not (in_asia or in_ny):
        return None

    # 3. Filter HTF High-Probability Confluence
    h1_momentum = detect_htf_momentum(h1_bars)     # "BEARISH", "BULLISH", atau "NEUTRAL"
    m30_momentum = detect_htf_momentum(m30_bars)   # "BEARISH", "BULLISH", atau "NEUTRAL"

    if h1_momentum == "NEUTRAL" or h1_momentum != m30_momentum:
        return None  # Tidak ada keselarasan arah HTF

    # 4. Evaluasi Momentum Candle M15 (Candle yang baru close [-1])
    c = m15_bars[-1]
    body = abs(c.close - c.open)
    total_range = c.high - c.low
    atr14 = compute_atr(m15_bars, 14)

    if total_range <= 0 or (body / total_range < 0.65) or (total_range < 1.5 * atr14):
        return None  # Bukan momentum candle yang valid

    # 5. Penarikan Fibonacci Sesuai Aturan Wick vs Body
    if h1_momentum == "BEARISH" and c.close < c.open:
        # Awal Momentum (Level 1.0): High jika ada wick atas, Open jika tidak ada
        lvl_1 = c.high if (c.high > c.open) else c.open
        # Akhir Momentum (Level 0.0): Low jika ada wick bawah, Close jika tidak ada
        lvl_0 = c.low if (c.low < c.close) else c.close
        
        delta = lvl_1 - lvl_0
        if delta <= 0:
            return None

        # Level Retest
        retest_236 = lvl_0 + (0.236 * delta)
        retest_500 = lvl_0 + (0.500 * delta)
        retest_618 = lvl_0 + (0.618 * delta)
        retest_786 = lvl_0 + (0.786 * delta)
        tp_extension = lvl_0 - (0.270 * delta)

        return {
            "side": "SHORT",
            "anchor_1_0": lvl_1,
            "anchor_0_0": lvl_0,
            "retest_levels": {
                "0.236": retest_236,
                "0.500": retest_500,
                "0.618": retest_618,
                "0.786": retest_786
            },
            "stop_loss": lvl_1 + 0.20,  # Level 1.0 + buffer
            "take_profit_1": lvl_0,     # Level 0.0
            "take_profit_2": tp_extension, # Level -0.27
            "max_wait_bars": 4
        }

    elif h1_momentum == "BULLISH" and c.close > c.open:
        # Awal Momentum (Level 1.0): Low jika ada wick bawah, Open jika tidak ada
        lvl_1 = c.low if (c.low < c.open) else c.open
        # Akhir Momentum (Level 0.0): High jika ada wick atas, Close jika tidak ada
        lvl_0 = c.high if (c.high > c.close) else c.close
        
        delta = lvl_0 - lvl_1
        if delta <= 0:
            return None

        # Level Retest
        retest_236 = lvl_0 - (0.236 * delta)
        retest_500 = lvl_0 - (0.500 * delta)
        retest_618 = lvl_0 - (0.618 * delta)
        retest_786 = lvl_0 - (0.786 * delta)
        tp_extension = lvl_0 + (0.270 * delta)

        return {
            "side": "LONG",
            "anchor_1_0": lvl_1,
            "anchor_0_0": lvl_0,
            "retest_levels": {
                "0.236": retest_236,
                "0.500": retest_500,
                "0.618": retest_618,
                "0.786": retest_786
            },
            "stop_loss": lvl_1 - 0.20,  # Level 1.0 - buffer
            "take_profit_1": lvl_0,     # Level 0.0
            "take_profit_2": tp_extension, # Level +1.27 / -0.27 expansion
            "max_wait_bars": 4
        }

    return None
```
