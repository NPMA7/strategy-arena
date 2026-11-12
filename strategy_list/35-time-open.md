# Spesifikasi Strategi #35: Opening Hour Range (`time_open`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **Opening Hour Range**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#35` · `time_open` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Waktu** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (`BarRing` kapasitas 1440 bar / 24 jam) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.8`** | Otomatis berdasarkan cluster `Waktu` |
| **Leverage Default** | **`12x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.10\% \text{ Forex} / 0.35\% \text{ Crypto})$ | Floor proteksi adaptif di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Opening Range Breakout (ORB) sejati: membentuk kotak High/Low 30 menit pertama saat sesi utama dibuka (Asia `00:00 UTC`, London `08:00 UTC`, New York `13:00 UTC`) dan masuk saat terjadi breakout konfirmasi keluar dari box tersebut.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. Identifikasi awal sesi dalam `s.ts[i]` (`00-02`, `08-09`, `13-14` UTC) pasca 30 menit pertama (`cur_ts >= box_end`).
2. Pindai hingga 180 bar ke belakang di dalam `BarRing` (kapasitas 1440 bar) untuk menentukan `or_high` & `or_low` dari jendela 30 menit pembukaan.
3. **BUY (+0.75)**: $C_i > \text{or\_high}$, $C_{i-1} \le \text{or\_high}$, dan $C_i > O_i$.
4. **SELL (-0.75)**: $C_i < \text{or\_low}$, $C_{i-1} \ge \text{or\_low}$, dan $C_i < O_i$.

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  [30m Opening Box High/Low] ---> Breakout Close > OR_High (Bull) ===> BUY (+0.75)
                             ---> Breakout Close < OR_Low  (Bear) ===> SELL (-0.75)
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
   - **Mode Forex MT5**: $\text{StopDist} = \max(2.0 \times \text{ATR}_{14}(M1), \; 0.0010 \times \text{Price})$ *(floor adaptif 0.10%)*
   - **Mode Spot & Futures**: $\text{StopDist} = \max(2.0 \times \text{ATR}_{14}(M1), \; 0.0035 \times \text{Price})$ *(floor 0.35%)*
   - $\text{TPDist} = 1.8 \times \text{StopDist}$
   - Jika muncul sinyal berlawanan arah (`pos.side != new_side`), posisi lama langsung ditutup (*reverse signal exit*) sebelum posisi baru dibuka.

---

## 5. Audit Risiko, Temuan Bug & Titik Lemah (*CRITICAL AUDIT*)

Hasil pemeriksaan langsung terhadap kode sumber `server/strategies.py`, `server/engine.py`, dan `server/forex_feed.py` menemukan catatan audit spesifik berikut untuk strategi ini:

* **✅ FIXED (Implementasi Opening Range Breakout Sejati)**: Sebelumnya hanyalah `trend_stack` selama 4 jam pagi UTC. Kini didukung sejarah `1440` bar untuk membangun Box ORB 30-menit di pembukaan sesi Asia, London, dan New York.
* **ℹ️ Pembaruan Mesin M1 (`0.10% Forex SL Floor` & `1440-Bar History`)**: `engine.py` kini menurunkan batas SL minimum khusus mode **Forex MT5** dari `0.35%` menjadi **`0.10%`** (membuat target & stop jauh lebih proporsional pada pasangan Forex & XAUUSD), sementara mode Spot & Futures menjaga floor `0.35%`. Buffer data M1 diperbesar ke `1440 bar` (24 jam).

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'time_open':
def opening_range_breakout(s):
    """Opening Hour Range Breakout (30m opening box pada awal sesi Asia/London/NY)."""
    i = s.i
    if i < 60 or not _ok(s.c[i], s.c[i - 1], s.ts[i]):
        return 0.0
    cur_ts = int(s.ts[i])
    hour = (cur_ts // 3_600_000) % 24
    # Sesi aktif 2-3 jam pasca open utama: Asia 00-02, London 08-10, NY 13-15 UTC
    if 0 <= hour < 3:
        sess_start_hr = 0
    elif 8 <= hour < 10:
        sess_start_hr = 8
    elif 13 <= hour < 15:
        sess_start_hr = 13
    else:
        return 0.0
    day_ms = (cur_ts // 86_400_000) * 86_400_000
    box_start = day_ms + sess_start_hr * 3_600_000
    box_end = box_start + 30 * 60_000
    if cur_ts < box_end:
        return 0.0
    or_high = None
    or_low = None
    for k in range(max(0, i - 180), i):
        tk = int(s.ts[k])
        if box_start <= tk < box_end:
            or_high = s.h[k] if or_high is None else max(or_high, s.h[k])
            or_low = s.l[k] if or_low is None else min(or_low, s.l[k])
    if or_high is None or or_low is None or or_high <= or_low:
        return 0.0
    if s.c[i] > or_high and s.c[i - 1] <= or_high and s.c[i] > s.o[i]:
        return 0.75
    if s.c[i] < or_low and s.c[i - 1] >= or_low and s.c[i] < s.o[i]:
        return -0.75
    return 0.0
```
