# Spesifikasi Strategi #84: XAUUSD MC-FIBO Retest (`fx_xauusd_mc_fibo`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **XAUUSD MC-FIBO Retest**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#84` · `fx_xauusd_mc_fibo` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Fibonacci** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (1-Menit Bar Closed via `BarRing`) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.8`** | Otomatis berdasarkan cluster `Fibonacci` |
| **Leverage Default** | **`1x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.35\% \times \text{Harga})$ | Floor proteksi minimum 0.35% di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Implementasi awal strategi khusus `XAUUSD` berbasis Candle Momentum `M15`, konfirmasi keselarasan arah `M30` & `H1`, filter sesi Asia (`00–06 UTC`) & New York (`12–20 UTC`), serta penarikan Fibonacci fleksibel (Wick vs Body) pada candle momentum.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. Resampling `Snap` (`M1`, $W=320$ bar) ke `M15`, `M30`, `H1` via bucket timestamp (`ix.size >= minutes // 2`).
2. Filter instrumen `symbol == 'XAUUSD'` & sesi UTC `00–05` atau `12–19`.
3. Tren `H1` & `M30` searah (`fast vs slow`, `body_ratio >= 0.45`).
4. Candle `m15[-1]` searah `h1_dir`, `body/rng >= 0.65`, dan `rng >= 1.5 * ATR_14(M15)`.
5. Anchor Fibo `origin`/`terminal` (wick vs body), cek retest `[0.236..0.786]` lalu return `h1_dir * 0.9` jika valid atau `h1_dir * 0.75` jika tidak.

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  H1 & M30 Searah + M15 Momentum >= 1.5 ATR ---> Cek Zone 0.236..0.786 ---> ENTRY (0.9 / 0.75)
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

* **🚨 CRITICAL BUG #1 (Entry Langsung Tanpa Menunggu Retest!)**: Baris 1111–1118 `strategies.py` mengecek apakah close `m15[-1]` berada di zona `[0.236, 0.786]`, tetapi di baris 1118 jika `valid` bernilai `False`, fungsi **TETAP MERETURN `h1_dir * 0.75`** (`> THRESHOLD 0.15`)! Akibatnya bot langsung Open Market Order pada penutupan impuls tanpa pernah menunggu retest ke level `0.236 / 0.5 / 0.786`.
* **🚨 CRITICAL BUG #2 (M15 Belum Close & Sinyal Berulang 1x/Menit)**: Fungsi `aggregate(15)` menerima grup dengan `ix.size >= 7` menit (`minutes // 2`), sehingga candle `m15[-1]` yang masih berjalan dari menit ke-7 sampai ke-14 terus memicu sinyal berulang setiap 1 menit, bukan menunggu close M15 utuh.
* **⚠️ Keterbatasan Window `Snap` (`W=320` Bar = 5.3 Jam)**: Karena `Snap` hanya menampung 320 bar M1, hasil resampling `H1` maksimal hanya 5–6 bar. Akibatnya `closes[-20:]` di `direction(h1)` tidak pernah terbentuk (`fast = closes[-1]` vs rata-rata 3–5 bar saja).
* **⚠️ Engine Mengabaikan SL Fibo `1` & TP `-0.27`**: `engine.py` masih mengenakan TP/SL berbasis `ATR_14(M1)` (`1:1.8`) dengan minimum SL `0.35%`, bukan anchor level `1` (open/wick momentum M15) dan `-0.27` sesuai blueprint `xauusd-momentum-candle-fibonacci.md`.
* **⚠️ Catatan Umum Mesin M1 (`0.35% Minimum SL Floor`)**: Karena sinyal dievaluasi pada bar **1-menit (`M1`)**, sedangkan `engine.py` memaksa jarak Stop Loss minimal `0.35%` (~143 pips pada XAUUSD atau ~39 pips pada EURUSD), strategi jangka pendek M1 harus menahan fluktuasi lebar yang kerap tidak sebanding dengan target scalping-nya.

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'fx_xauusd_mc_fibo':
def fx_xauusd_mc_fibo(s):
    """XAUUSD M15 momentum candle + M30/H1 alignment + Fibonacci retest zones.

    Snap contains M1 bars. Resampling here keeps strategy isolated from feed and
    makes the timeframe rules explicit. Signal fires only on a completed M15 bar.
    """
    if s.i < 120 or not _ok(s.c[s.i], s.ts[s.i]):
        return 0.0

    # Strategy is XAUUSD-only; engine passes symbol indirectly through Snap.
    # Forex feed has no symbol field, so mark supported symbols in engine before call.
    symbol = getattr(s, "symbol", None)
    if symbol != "XAUUSD":
        return 0.0

    import numpy as np

    def aggregate(minutes):
        bucket = (s.ts.astype(np.int64) // (minutes * 60_000))
        groups = []
        for key in np.unique(bucket):
            ix = np.flatnonzero(bucket == key)
            if ix.size < max(1, minutes // 2):
                continue
            groups.append((s.ts[ix[-1]], s.o[ix[0]], s.h[ix].max(), s.l[ix].min(), s.c[ix[-1]]))
        return groups

    m15, m30, h1 = aggregate(15), aggregate(30), aggregate(60)
    if len(m15) < 16 or len(m30) < 4 or len(h1) < 3:
        return 0.0

    # UTC session filter: Asia 00-06, New York 12-20.
    hour = int((m15[-1][0] // 3_600_000) % 24)
    if not (0 <= hour < 6 or 12 <= hour < 20):
        return 0.0

    def direction(bars):
        if len(bars) < 3:
            return 0
        closes = np.array([x[4] for x in bars], dtype=float)
        fast = closes[-1] if len(closes) < 20 else closes[-20:].mean()
        slow = closes.mean()
        last = bars[-1]
        body_ratio = abs(last[4] - last[1]) / max(last[2] - last[3], 1e-12)
        if body_ratio < 0.45 or abs(fast - slow) / max(slow, 1e-12) < 0.00015:
            return 0
        return 1 if last[4] > last[1] and fast > slow else -1 if last[4] < last[1] and fast < slow else 0

    h1_dir, m30_dir = direction(h1), direction(m30)
    if not h1_dir or h1_dir != m30_dir:
        return 0.0

    _, o, h, l, c = m15[-1]
    atr_ranges = np.array([x[2] - x[3] for x in m15[-15:-1]], dtype=float)
    atr14 = atr_ranges.mean() if atr_ranges.size else 0.0
    rng, body = h - l, abs(c - o)
    if rng <= 0 or atr14 <= 0 or body / rng < 0.65 or rng < 1.5 * atr14:
        return 0.0
    if (h1_dir > 0 and c <= o) or (h1_dir < 0 and c >= o):
        return 0.0

    # Fibonacci anchors follow wick/body rule from specification.
    origin = l if h1_dir > 0 and l < o else o if h1_dir > 0 else h if h > o else o
    terminal = h if h1_dir > 0 and h > c else c if h1_dir > 0 else l if l < c else c
    delta = abs(terminal - origin)
    if delta <= 0:
        return 0.0

    # Retest confirmation: current M15 close must remain inside 0.236-0.786.
    if h1_dir > 0:
        levels = [terminal - x * delta for x in (0.236, 0.5, 0.786)]
        valid = min(levels) <= c <= max(levels)
    else:
        levels = [terminal + x * delta for x in (0.236, 0.5, 0.786)]
        valid = min(levels) <= c <= max(levels)
    return float(h1_dir * 0.9) if valid else float(h1_dir * 0.75)
```
