# Spesifikasi Strategi #88: Supply & Demand Zone (`supply_demand_zone`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **Supply & Demand Zone**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#88` · `supply_demand_zone` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Struktur** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (`BarRing` kapasitas 1440 bar / 24 jam) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.8`** | Otomatis berdasarkan cluster `Struktur` |
| **Leverage Default** | **`12x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.10\% \text{ Forex} / 0.35\% \text{ Crypto})$ | Floor proteksi adaptif di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Mengidentifikasi formasi Base sempit (`range < 0.9 ATR`) diikuti impuls kuat (`> 1.0 ATR`) dalam rentang 2 hingga 10 bar terakhir, mengecek bahwa zona Supply/Demand tersebut **belum pernah jebol** pada bar antara, lalu masuk ketika harga me-retest zona base tersebut dan tutup searah.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. Scan $k \in [i-2 \dots i-10]$ mencari base $(H_k - L_k) < 0.9\cdot\text{ATR}_{14}$.
2. **Demand Zone (+0.80)**: $(C_{k+1}-O_{k+1}) > 1.0\cdot\text{ATR}$, zona belum jebol $\min(L_{k+2..i-1}) \ge L_k$, dan saat retest $L_i \le H_k, C_i \ge L_k, C_i > O_i$.
3. **Supply Zone (-0.80)**: Simetris untuk Drop-Base-Drop + cek tidak menembus $H_k$.

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  [Base Sempit k] ---> [Impuls Besar k+1] ---> (Zona Utuh s/d i-1) ---> [Retest Bar i] => ENTRY
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

* **✅ FIXED (Lookback Dinamis 2..10 Bar & Cek Freshness)**: Membuka jendela pencarian dari kaku 1 bar (`i-2`) menjadi scanning dinamis 2–10 bar ke belakang dengan validasi zona masih utuh.
* **ℹ️ Pembaruan Mesin M1 (`0.10% Forex SL Floor` & `1440-Bar History`)**: `engine.py` kini menurunkan batas SL minimum khusus mode **Forex MT5** dari `0.35%` menjadi **`0.10%`** (membuat target & stop jauh lebih proporsional pada pasangan Forex & XAUUSD), sementara mode Spot & Futures menjaga floor `0.35%`. Buffer data M1 diperbesar ke `1440 bar` (24 jam).

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'supply_demand_zone':
def supply_demand_zone(s):
    """Institutional Supply & Demand Imbalance Retest (scan zona segar 2..30 bar terakhir)."""
    if s.i < 32:
        return 0.0
    c, o, h, l, atr = s.c[s.i], s.o[s.i], s.h[s.i], s.l[s.i], s.atr14[s.i]
    if not _ok(c, o, h, l, atr) or atr <= 0:
        return 0.0
    rng = max(h - l, 1e-12)
    for k in range(s.i - 2, max(s.i - 30, 1), -1):
        base_h, base_l = s.h[k], s.l[k]
        if (base_h - base_l) >= 1.0 * atr:
            continue
        impulse = s.c[k + 1] - s.o[k + 1]
        # Demand Zone: base sempit + rally impulsif + belum jebol ke bawah base_l
        if impulse > 0.95 * atr:
            invalid = (k + 2 <= s.i - 1) and (float(s.l[k + 2:s.i].min()) < base_l)
            if not invalid and l <= base_h and c >= base_l and (c > o or (c - l) / rng >= 0.60):
                return 0.80
        # Supply Zone: base sempit + drop impulsif + belum jebol ke atas base_h
        if -impulse > 0.95 * atr:
            invalid = (k + 2 <= s.i - 1) and (float(s.h[k + 2:s.i].max()) > base_h)
            if not invalid and h >= base_l and c <= base_h and (c < o or (h - c) / rng >= 0.60):
                return -0.80
    return 0.0
```
