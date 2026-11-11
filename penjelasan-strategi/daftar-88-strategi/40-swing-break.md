# Spesifikasi Strategi #40: Swing Volume Break (`swing_break`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **Swing Volume Break**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#40` · `swing_break` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Price action** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (1-Menit Bar Closed via `BarRing`) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.8`** | Otomatis berdasarkan cluster `Price action` |
| **Leverage Default** | **`10x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.35\% \times \text{Harga})$ | Floor proteksi minimum 0.35% di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Breakout rentang swing 9-bar yang divalidasi oleh buffer 0.25×ATR dan peningkatan volume.

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. **BUY**: $C_i > \max(H_{i-10..i-2}) + 0.25 \cdot \text{ATR}_{14}$ dan $V_i > V_{i-1}$
2. **SELL**: $C_i < \min(L_{i-10..i-2}) - 0.25 \cdot \text{ATR}_{14}$ dan $V_i > V_{i-1}$

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  Swing High + 0.25*ATR  <=== Breakout + Vol[i] > Vol[i-1] = BUY
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

* **⚠️ Ketergantungan Pada Volume Tick Acak di Forex**: Di Forex, `V[i] > V[i-1]` bernilai acak ~50% karena volume disimulasikan oleh `random.uniform` per tick.
* **⚠️ Catatan Umum Mesin M1 (`0.35% Minimum SL Floor`)**: Karena sinyal dievaluasi pada bar **1-menit (`M1`)**, sedangkan `engine.py` memaksa jarak Stop Loss minimal `0.35%` (~143 pips pada XAUUSD atau ~39 pips pada EURUSD), strategi jangka pendek M1 harus menahan fluktuasi lebar yang kerap tidak sebanding dengan target scalping-nya.

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk 'swing_break':
def swing_break(s):
    i = s.i
    if i < 10:
        return 0.0
    h = float(s.h[i - 10:i - 1].max())
    l = float(s.l[i - 10:i - 1].min())
    atr = s.atr14[i]
    if not _ok(atr) or atr <= 0:
        return 0.0
    if s.c[i] > h + 0.25 * atr and s.v[i] > s.v[i - 1]:
        return 0.6
    if s.c[i] < l - 0.25 * atr and s.v[i] > s.v[i - 1]:
        return -0.6
    return 0.0
```
