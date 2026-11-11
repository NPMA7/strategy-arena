# Spesifikasi Strategi #79: SMC Order Block Mitigation (`smc_orderblock`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **SMC Order Block Mitigation**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#79` · `smc_orderblock` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **ICT** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (`BarRing` kapasitas 1440 bar / 24 jam) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.8`** | Otomatis berdasarkan cluster `ICT` |
| **Leverage Default** | **`15x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.10\% \text{ Forex} / 0.35\% \text{ Crypto})$ | Floor proteksi adaptif di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Memindai 2 hingga 12 candle ke belakang untuk mencari candle berlawanan terakhir sebelum gelombang pergerakan kuat (`> 1.1 ATR`), **memverifikasi bahwa zona Order Block tersebut masih fresh/unmitigated** (belum ditembus invalidasi di bar antara), lalu entry saat candle saat ini me-retest zona OB dan tutup searah.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. Loop $k \in [i-2 \dots i-12]$ mencari Bullish OB ($C_k < O_k$ & $(C_{k+1}-C_k) > 1.1\cdot\text{ATR}$).
2. Validasi fresh: $\min(L_{k+1..i-1}) \ge L_k$ (jika sudah tembus ke bawah `ob_low`, `continue` cari OB berikutnya).
3. **BUY (+0.80)**: Candle $i$ menyentuh $[L_k, H_k]$ dan $C_i > O_i$ (mirror simetris Bearish OB `-0.80`).

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  OB Bar [k] ===> Displacement [k+1] ===> [Cek Freshness k+1..i-1] ===> Retest + Close Searah => ENTRY
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

* **✅ FIXED (Cek Freshness & Skip OB Invalidasi)**: Sebelumnya loop langsung `break` pada OB pertama meskipun OB tersebut sudah jebol/invalidasi di bar tengah. Kini menggunakan `continue` hingga menemukan OB fresh yang belum jebol.
* **ℹ️ Pembaruan Mesin M1 (`0.10% Forex SL Floor` & `1440-Bar History`)**: `engine.py` kini menurunkan batas SL minimum khusus mode **Forex MT5** dari `0.35%` menjadi **`0.10%`** (membuat target & stop jauh lebih proporsional pada pasangan Forex & XAUUSD), sementara mode Spot & Futures menjaga floor `0.35%`. Buffer data M1 diperbesar ke `1440 bar` (24 jam).

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'smc_orderblock':
def smc_orderblock(s):
    """Institutional Order Block Mitigation (SMC)."""
    if s.i < 15:
        return 0.0
    c, o, h, l, atr = s.c[s.i], s.o[s.i], s.h[s.i], s.l[s.i], s.atr14[s.i]
    if not _ok(c, o, h, l, atr) or atr <= 0:
        return 0.0
    for k in range(s.i - 2, max(s.i - 12, 1), -1):
        if s.c[k] < s.o[k] and (s.c[k + 1] - s.c[k]) > 1.1 * atr:
            ob_high, ob_low = s.h[k], s.l[k]
            if float(s.l[k + 1:s.i].min()) < ob_low:
                continue
            if l <= ob_high and c >= ob_low and c > o:
                return 0.80
    for k in range(s.i - 2, max(s.i - 12, 1), -1):
        if s.c[k] > s.o[k] and (s.c[k] - s.c[k + 1]) > 1.1 * atr:
            ob_high, ob_low = s.h[k], s.l[k]
            if float(s.h[k + 1:s.i].max()) > ob_high:
                continue
            if h >= ob_low and c <= ob_high and c < o:
                return -0.80
    return 0.0
```
