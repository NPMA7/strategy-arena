# Spesifikasi Strategi #75: Camarilla Multi-Confluence (`camarilla_fader`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **Camarilla Multi-Confluence**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#75` · `camarilla_fader` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Struktur** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (`BarRing` kapasitas 1440 bar / 24 jam) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.8`** | Otomatis berdasarkan cluster `Struktur` |
| **Leverage Default** | **`12x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.10\% \text{ Forex} / 0.35\% \text{ Crypto})$ | Floor proteksi adaptif di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Camarilla Pivot Points klasik yang dihitung dari blok range 60 bar sebelumnya (`H3/H4` sebagai zona resistance jenuh, `L3/L4` sebagai zona support jenuh) untuk mengeksekusi pantulan *mean reversion* di dalam koridor L3–H3 selama tidak menembus level breakout L4/H4.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. Dari `[i-61 : i-1]`: $\text{rng} = H_{60} - L_{60}$, $\;P_C = C_{i-2}$.
2. $H_3 = P_C + 1.1\cdot\text{rng}/4$, $\;H_4 = P_C + 1.1\cdot\text{rng}/2$, $\;L_3 = P_C - 1.1\cdot\text{rng}/4$, $\;L_4 = P_C - 1.1\cdot\text{rng}/2$.
3. **BUY (+0.75)**: $L_i \le L_3$ dan $C_i > L_3$ dan $C_i > L_4$ dan $C_i > O_i$.
4. **SELL (-0.75)**: $H_i \ge H_3$ dan $C_i < H_3$ dan $C_i < H_4$ dan $C_i < O_i$.

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  Test H3 + Reject < H3 & > Open (di dalam H4) ===> SELL (-0.75)
  Test L3 + Bounce > L3 & > Open (di atas L4)  ===> BUY  (+0.75)
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

* **✅ FIXED (Implementasi Level Camarilla H3/H4/L3/L4 Sejati)**: Menggantikan syarat lama `Close < LL20` dengan formula Pivot Camarilla `1.1/4` & `1.1/2` dari blok 60-bar sebelumnya.
* **ℹ️ Pembaruan Mesin M1 (`0.10% Forex SL Floor` & `1440-Bar History`)**: `engine.py` kini menurunkan batas SL minimum khusus mode **Forex MT5** dari `0.35%` menjadi **`0.10%`** (membuat target & stop jauh lebih proporsional pada pasangan Forex & XAUUSD), sementara mode Spot & Futures menjaga floor `0.35%`. Buffer data M1 diperbesar ke `1440 bar` (24 jam).

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'camarilla_fader':
def camarilla_fader(s):
    """Camarilla Pivot Points Multi-Confluence (L3/H3 Fade & L4/H4 Breakout dari blok 60-bar)."""
    i = s.i
    if i < 62 or not _ok(s.c[i], s.h[i], s.l[i], s.o[i]):
        return 0.0
    prev_h = float(s.h[i - 60:i].max())
    prev_l = float(s.l[i - 60:i].min())
    prev_c = float(s.c[i - 1])
    rng = prev_h - prev_l
    if rng <= 0:
        return 0.0
    h3 = prev_c + rng * 1.1 / 4.0
    h4 = prev_c + rng * 1.1 / 2.0
    l3 = prev_c - rng * 1.1 / 4.0
    l4 = prev_c - rng * 1.1 / 2.0
    c, o, h, l = s.c[i], s.o[i], s.h[i], s.l[i]
    low2 = min(l, float(s.l[i - 1]))
    high2 = max(h, float(s.h[i - 1]))
    # Mean-reversion bounce L3/H3 (1 atau 2 bar retest & reclaim)
    if low2 <= l3 and c > l3 and c > o and c > l4:
        return 0.75
    if high2 >= h3 and c < h3 and c < o and c < h4:
        return -0.75
    # Breakout H4/L4 dengan konfirmasi penutupan & EMA21
    e21 = s.ema21[i]
    if _ok(e21):
        if prev_c <= h4 and c > h4 and c > o and c > e21:
            return 0.80
        if prev_c >= l4 and c < l4 and c < o and c < e21:
            return -0.80
    return 0.0
```
