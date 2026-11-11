# Indeks Dokumentasi & Penjelasan Strategi Strategy Arena

Folder ini berisi spesifikasi teknis, aturan logika algoritmik, potongan kode sumber, dan analisis audit dari seluruh strategi di Strategy Arena & Copy-Trade Engine.

---

## Daftar Berkas Dokumentasi

1. 📘 [**Katalog & Bedah Logika 88 Strategi (katalog-88-strategi.md)**](./katalog-88-strategi.md)
   - Berisi dokumentasi teknis lengkap dari **ke-88 strategi** yang saat ini aktif berjalan di Strategy Arena (Forex MT5, Binance Futures, & Binance Spot).
   - Dilengkapi tabel master (#1 s/d #88), potongan kode Python, rasio Risk-to-Reward, leverage, serta **Audit Checklist (titik lemah dan potensi bug)**.

2. 📙 [**Momentum Candle Fibonacci Retest (xauusd-momentum-candle-fibonacci.md)**](./xauusd-momentum-candle-fibonacci.md)
   - Spesifikasi detail strategi baru khusus XAUUSD M15 dengan filter HTF (M30 & H1) dan aturan penarikan Fibonacci fleksibel (Wick vs Body).
   - Disiapkan sebagai acuan implementasi/ekspansi algoritma untuk agent AI (Claude Opus 3.5, GPT, Astra).
