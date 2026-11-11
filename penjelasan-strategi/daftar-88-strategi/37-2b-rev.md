# Spesifikasi Strategi #37: 2B Reversal (`2b_rev`)

Dokumen ini memuat bedah arsitektur logika, spesifikasi matematis, mekanisme eksekusi di Arena Engine, serta **hasil audit kode aktual** untuk strategi **2B Reversal**. Dokumen ini disusun secara terstruktur agar mudah ditinjau oleh trader maupun agent AI (Claude Opus 3.5, GPT, Astra) untuk mendeteksi bug, memperbaiki kelemahan, dan mengembangkan versi optimalnya.

---

## 1. Parameter Dasar & Lingkup Trading

| Parameter | Nilai / Aturan Aktual di Engine | Keterangan |
| :--- | :--- | :--- |
| **Nomor & ID Strategi** | `#37` · `2b_rev` | Terdaftar di `server/strategies.py` |
| **Kategori / Cluster** | **Price action** | Menentukan profil rasio R:R otomatis |
| **Target Pasar** | Universal (Forex MT5, Binance Futures, Spot) | Spot: Long-Only · Futures & Forex: Long + Short |
| **Timeframe Evaluasi** | `M1` (1-Menit Bar Closed via `BarRing`) | Dieksekusi 1x setiap bar 1-menit selesai ditutup |
| **Ambang Pemicu Skor** | `score > +0.15` (LONG) / `score < -0.15` (SHORT) | Skala output sinyal `[-1.0 .. +1.0]` |
| **Rasio Risk-to-Reward (R:R)** | **`1 : 1.8`** | Otomatis berdasarkan cluster `Price action` |
| **Leverage Default** | **`10x`** (Futures) · **`1x MT5 Direct`** (Forex) | Di Forex menggunakan lot sizing risiko 1.5% modal (~$15) |
| **Stop Loss Engine** | $\max(2.0 \times \text{ATR}_{14}, \; 0.35\% \times \text{Harga})$ | Floor proteksi minimum 0.35% di `engine.py` |

---

## 2. Filosofi Strategi & Konsep Pasar

Mendeteksi kegagalan penembusan swing 4-bar sebelumnya (pola 2B Reversal klasik).

---

## 3. Kriteria Matematis & Logika Deteksi Sinyal

1. $H_2 = \max(H_{i-5..i-2})$, $L_2 = \min(L_{i-5..i-2})$
2. **SELL**: $H_{i-1} > H_2$ dan $H_i < H_{i-1}$ dan $C_i < C_{i-1}$
3. **BUY**: $L_{i-1} < L_2$ dan $L_i > L_{i-1}$ dan $C_i > C_{i-1}$

### Visualisasi Alur Sinyal (Diagram Logika):
```text
  Swing High (H2) -----
                       /\ (H[i-1] tembus H2)
                      /  \ (H[i] & C[i] lebih rendah) ===> SELL
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

* **🚨 DUPLIKAT 100% DENGAN #55 `price_action_2b`**: Di screenshot leaderboard Anda, terlihat #75 (`2B Reversal -4.53%`) dan #76 (`2B Reversal -4.53%`) dengan PnL kembar identik karena keduanya menunjuk ke fungsi `price_action_2b` yang sama persis!
* **⚠️ Syarat Terlalu Longgar**: Tidak memverifikasi apakah penutupan `c[i]` sudah kembali ke bawah `h2` (konfirmasi *false breakout*), melainkan hanya melihat satu bar lower high + lower close, sehingga sering masuk di tengah pullback normal.
* **⚠️ Catatan Umum Mesin M1 (`0.35% Minimum SL Floor`)**: Karena sinyal dievaluasi pada bar **1-menit (`M1`)**, sedangkan `engine.py` memaksa jarak Stop Loss minimal `0.35%` (~143 pips pada XAUUSD atau ~39 pips pada EURUSD), strategi jangka pendek M1 harus menahan fluktuasi lebar yang kerap tidak sebanding dengan target scalping-nya.

---

## 6. Implementasi Kode Aktual (Python Source)

Berikut adalah implementasi kode aktual yang saat ini berjalan di produksi (`server/strategies.py`), siap diaudit dan dikembangkan lebih lanjut oleh tim agent AI (**Claude Opus 3.5**, **GPT**, **Astra**):

```python
# Sumber aktual dari server/strategies.py untuk '2b_rev':
def price_action_2b(s):
    """Reversal 2B: dua kali gagal menembus swing dengan wick panjang."""
    i = s.i
    if i < 6:
        return 0.0
    h2 = float(s.h[i - 5:i - 1].max())
    l2 = float(s.l[i - 5:i - 1].min())
    if s.h[i - 1] > h2 and s.h[i] < s.h[i - 1] and s.c[i] < s.c[i - 1]:
        return -0.6
    if s.l[i - 1] < l2 and s.l[i] > s.l[i - 1] and s.c[i] > s.c[i - 1]:
        return 0.6
    return 0.0
```
