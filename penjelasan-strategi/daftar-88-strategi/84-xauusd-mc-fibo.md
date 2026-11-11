# Spesifikasi Strategi #84: XAUUSD MC-FIBO Retest (`xauusd_mc_fibo`)

Dokumen ini memuat blueprint arsitektur logika dan spesifikasi algoritmik dari strategi **Momentum Candle Fibonacci Retest**. Dokumen ini diformat secara presisi agar dapat dibaca, dianalisis, dan dikembangkan lebih lanjut oleh agent AI (seperti Claude, atau GPT) serta diimplementasikan ke dalam bot trading / backend Strategy Arena.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Spesifikasi / Aturan | Keterangan |
| :--- | :--- | :--- |
| **Simbol Target** | Forex: `XAUUSD` Only; Spot/Futures: semua pair aktif | Mode Forex dibatasi ketat ke `XAUUSD`; Crypto Spot/Futures universal |
| **Timeframe Eksekusi (LTF)** | `M15` (15-Menit) | Pembacaan momentum candle dan eksekusi entry |
| **Timeframe Konfirmasi (HTF)**| `M30` & `H1` | Filter arah tren & validasi momentum probabilitas tinggi |
| **Filter Sesi Waktu** | **Sesi Asia** & **Sesi New York** | Menghindari fase konsolidasi / whipsaw di luar likuiditas utama |
| **Model Eksekusi** | Limit Order / Retest Market Execution | Menunggu harga retest ke zona diskon Fibonacci |
| **Rasio Risk-to-Reward (R:R)**| **1 : 1.5** hingga **1 : 3.5** | Asimetris dengan Stop Loss ketat di origin momentum |

---

### Cakupan Implementasi Arena

- **Forex:** strategy aktif **hanya pada `XAUUSD`**.
- **Spot/Futures:** strategy aktif pada semua pair feed. Aturan candle, HTF, sesi, Fibonacci (`s.custom_sl_tp`), dan risk management tetap sama.
- Feed Arena berupa candle M1 (`BarRing` berkapasitas `1440` bar = 24 jam penuh). Backend meresampling bar tertutup (*completed*) menjadi M15, M30, dan H1 tanpa *mid-candle repainting*.
- Level SL (`1.0`) dan TP (`-0.27`) dikirim presisi via `s.custom_sl_tp = (origin, tp_neg_027)` ke `engine._resolve_stops()` (bukan `0.35%` generik).

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
   - Jam WIB: **07:00 – 13:59 WIB** (00:00 – 06:59 UTC / `0 <= hour < 7`).
2. **Sesi New York (US Session & Overlap London)**:
   - Jam WIB: **19:00 – 03:59 WIB** (12:00 – 20:59 UTC / `12 <= hour < 21`).
3. **Di luar kedua sesi ini**: Bot tidak membuka setup baru (*No Trade*).

---

## 7. Pseudocode Desain Awal (Referensi Pengembang)

```python
# ==============================================================================
# ALGORITHMIC SPECIFICATION: MC-FIBO (XAUUSD M15)
# ==============================================================================

def evaluate_mc_fibo_strategy(symbol, current_utc_hour, m15_bars, m30_bars, h1_bars):
    # 1. Filter Pair
    # Forex: hanya XAUUSD. Spot/Futures: semua pair feed.
    is_forex = market_mode == "forex"
    if is_forex and symbol != "XAUUSD":
        return None

    # 2. Filter Sesi (Asia: 00-07 UTC, NY: 12-21 UTC)
    in_asia = (0 <= current_utc_hour < 7)
    in_ny = (12 <= current_utc_hour < 21)
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

---

## 8. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`):

```python
# Sumber aktual dari server/strategies.py untuk 'xauusd_mc_fibo':
def xauusd_mc_fibo(s):
    """M15 Momentum Candle + M30/H1 alignment + Fibonacci [0.236..0.786] retest zones.

    Strict specs:
    - Forex mode: XAUUSD only. Spot/Futures: all pairs.
    - Completed M15/M30/H1 bars only (no mid-candle repainting).
    - Asia (00-07 UTC) & New York (12-21 UTC) sessions only.
    - Anchors: wick/body extreme for 1.0 (SL) & 0.0, TP = -0.27.
    - Fires ONLY when price genuinely retests inside [0.236, 0.786] without invalidation.
    """
    if s.i < 180 or not _ok(s.c[s.i], s.ts[s.i]):
        return 0.0

    symbol = getattr(s, "symbol", None)
    if getattr(s, "market_mode", "forex") == "forex" and symbol != "XAUUSD":
        return 0.0

    import numpy as np

    n = s.i + 1
    ts_a = s.ts[:n].astype(np.int64)
    o_a, h_a, l_a, c_a = s.o[:n], s.h[:n], s.l[:n], s.c[:n]

    # UTC session filter: Asia 00:00-06:59 UTC, New York 12:00-20:59 UTC
    hour = int((int(ts_a[-1]) // 3_600_000) % 24)
    if not (0 <= hour < 7 or 12 <= hour < 21):
        return 0.0

    def aggregate_closed(minutes: int):
        bucket = ts_a // (minutes * 60_000)
        cur_bucket = int(bucket[-1])
        cur_done = (((int(ts_a[-1]) // 60_000) + 1) % minutes) == 0
        min_bars = max(3, minutes // 3)
        groups = []
        for key in np.unique(bucket):
            k_int = int(key)
            if k_int == cur_bucket and not cur_done:
                continue
            ix = np.flatnonzero(bucket == key)
            if ix.size < min_bars:
                continue
            groups.append((
                k_int,
                int(ts_a[ix[-1]]),
                float(o_a[ix[0]]),
                float(h_a[ix].max()),
                float(l_a[ix].min()),
                float(c_a[ix[-1]]),
            ))
        return groups

    m15 = aggregate_closed(15)
    m30 = aggregate_closed(30)
    h1 = aggregate_closed(60)
    if len(m15) < 16 or len(m30) < 6 or len(h1) < 4:
        return 0.0

    def direction(bars):
        closes = np.array([x[5] for x in bars], dtype=float)
        fast = float(closes[-min(5, len(closes)):].mean())
        slow = float(closes[-min(20, len(closes)):].mean())
        if slow <= 0 or abs(fast - slow) / slow < 0.00008:
            return 0
        _, _, bo, bh, bl, bc = bars[-1]
        body_ratio = abs(bc - bo) / max(bh - bl, 1e-12)
        if body_ratio < 0.35:
            return 0
        if bc > bo and fast > slow:
            return 1
        if bc < bo and fast < slow:
            return -1
        return 0

    h1_dir, m30_dir = direction(h1), direction(m30)
    if not h1_dir or h1_dir != m30_dir:
        return 0.0

    px_now = float(c_a[-1])
    m1_m15_bucket = ts_a // (15 * 60_000)

    for idx_mc in range(len(m15) - 1, max(14, len(m15) - 4) - 1, -1):
        key_mc, _, o_mc, h_mc, l_mc, c_mc = m15[idx_mc]
        atr_ranges = np.array([x[3] - x[4] for x in m15[idx_mc - 14:idx_mc]], dtype=float)
        atr14 = float(atr_ranges.mean()) if atr_ranges.size else 0.0
        rng = h_mc - l_mc
        body = abs(c_mc - o_mc)
        if rng <= 0 or atr14 <= 0 or body / rng < 0.65 or rng < 1.5 * atr14:
            continue
        if (h1_dir > 0 and c_mc <= o_mc) or (h1_dir < 0 and c_mc >= o_mc):
            continue

        if h1_dir > 0:
            origin = l_mc if l_mc < o_mc else o_mc
            terminal = h_mc if h_mc > c_mc else c_mc
            delta = abs(terminal - origin)
            if delta <= 0:
                continue
            fibo_236 = terminal - 0.236 * delta
            fibo_786 = terminal - 0.786 * delta
            tp_neg_027 = terminal + 0.27 * delta
            after_ix = np.flatnonzero(m1_m15_bucket[:-1] > key_mc)
            if after_ix.size > 0:
                if float(l_a[after_ix].min()) <= origin or float(h_a[after_ix].max()) >= tp_neg_027:
                    continue
            if fibo_786 <= px_now <= fibo_236 and px_now > origin:
                s.custom_sl_tp = (origin, tp_neg_027)
                return 0.9
        else:
            origin = h_mc if h_mc > o_mc else o_mc
            terminal = l_mc if l_mc < c_mc else c_mc
            delta = abs(terminal - origin)
            if delta <= 0:
                continue
            fibo_236 = terminal + 0.236 * delta
            fibo_786 = terminal + 0.786 * delta
            tp_neg_027 = terminal - 0.27 * delta
            after_ix = np.flatnonzero(m1_m15_bucket[:-1] > key_mc)
            if after_ix.size > 0:
                if float(h_a[after_ix].max()) >= origin or float(l_a[after_ix].min()) <= tp_neg_027:
                    continue
            if fibo_236 <= px_now <= fibo_786 and px_now < origin:
                s.custom_sl_tp = (origin, tp_neg_027)
                return -0.9

    return 0.0
```
