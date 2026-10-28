# Strategy Arena — Terminal Kuantitatif & Mesin Simulasi Trading Real-Time

Platform terminal kuantitatif dan mesin simulasi *paper-trading* multi-strategi real-time berbasis **Python (FastAPI + AsyncPG)**, **PostgreSQL 17**, dan **Svelte 5 + Vite**. Sistem ini mengevaluasi dan mengadu puluhan algoritma kuantitatif secara simultan di 100 pasang aset kripto Binance dengan umpan data pasar live (*tick-by-tick*).

Dirancang dengan standar visual **Institutional Craft** (Anti-AI-Slop, *functional depth*, dark theme konsisten, border presisi 1px, tabel metrik densitas tinggi, serta bebas emoji generik).

---

## 🏛️ Arsitektur Sistem

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Binance Market Feed (REST & WS)                      │
│                  100 Pair USDT Spot & Futures Streams                  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Ring Buffer (250+ bar 1m)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                 Strategy Arena Engine (Dual Core)                      │
│  ┌──────────────────────────────┐    ┌──────────────────────────────┐  │
│  │     Spot Engine (39 Algoritma)│    │   Futures Engine (53 Algoritma)│ │
│  │   • Long-only / Akumulasi    │    │   • Long & Short (5x - 20x Lev)  │ │
│  │   • Cash $10.000 modal awal  │    │   • Funding Rate (0.01%/8j)      │ │
│  │   • Taker Fee 0.05%          │    │   • Liquidation & Auto-Refill MC │ │
│  └──────────────┬───────────────┘    └──────────────┬───────────────┘  │
└─────────────────┼───────────────────────────────────┼──────────────────┘
                  ▼                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│               PostgreSQL 17 (Buku Besar & Transaksi ACID)              │
│  • Antrean Buffer Transaksi Zero-Drop (Pending Trades & Signals)       │
│  • Sinkronisasi otomatis ledger akun & riwayat trade                   │
│  • Penyimpanan kurva ekuitas historis & metadata uptime                │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ WebSocket Broadcast & REST API
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     Frontend (Svelte 5 + Vite)                         │
│  • Papan Peringkat (BoardGrid) & Coming Soon R&D Blocks                │
│  • Strategy Dossier & Modal Analisis Mendalam (Canvas Crosshair)       │
│  • Visualisasi 3D WebGL Market Core & Feed-Forward Neural Network      │
│  • Hub Copy-Trading & Generator Kode Bot (Python / WS / cURL)          │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Fitur Utama

### 1. Dual-Core Real-Time Execution Engines
- **Spot Engine (39 Strategi)**: Fokus pada akumulasi spot, rotasi swing, dan *trend following* long-only tanpa risiko likuidasi utang leverage.
- **Futures Engine (53 Strategi)**: Mendukung posisi dua arah (**LONG & SHORT**) dengan leverage dinamis proporsional (5x hingga 20x).
- **Simulasi Biaya Pasar Nyata**:
  - *Taker Fee*: 0.05% per pembukaan dan penutupan posisi.
  - *Maker Fee*: 0.02%.
  - *Simulasi Funding Rate*: Rata-rata 0.01% setiap 8 jam sesuai data historis Binance.
  - *Mekanisme Margin Call (MC)*: Likuidasi darurat ketika margin habis, tercatat pada counter MC, dan auto-refill modal kembali ke $10.000 untuk pengujian ketahanan berkelanjutan.

### 2. Papan Peringkat Interaktif & Blok Coming Soon (R&D)
- **7-Column Grid Card Layout**: Kartu strategi responsif dengan sparkline SVG real-time dan titik status glow.
- **Multi-Kolom Sorting**: Urutkan strategi instan berdasarkan Ekuitas, Win Rate, Profit Factor, Total Trade, atau Drawdown.
- **Filter Kategori Terstruktur**: *Breakout*, *Fibonacci*, *ICT/SMC*, *Mean reversion*, *Momentum*, *Order flow*, *Statistik*, *Struktur*, *Volatility*, dan *Trend*.
- **Blok Strategi Coming Soon (R&D)**: Kartu terintegrasi yang menampilkan model kuantitatif yang sedang dalam tahap riset dan pengujian laboratorium internal (misal: *Order Flow Imbalance*, *Deep Q-Learning RL*, *Basis Carry Arbitrage*, *Transformer Alpha NLP*, dll.) lengkap dengan modal detail hipotesis model.

### 3. Strategy Dossier & Modal Analisis Mendalam
- **Multi-Timeframe Equity Curve**: Pemilihan rentang waktu fleksibel (24 Jam, 3 Hari, 7 Hari, 30 Hari, Semua / 2160 Jam) di atas kanvas grafik resolusi tinggi dengan inspeksi kursor crosshair interaktif.
- **Metrik Quant Lengkap (Bento Grid)**:
  - *Net PnL* & *Return %*
  - *Win Rate* (Sinkron 100% antara kartu, tab metrik, dan tabel trade)
  - *Profit Factor* (Gross Win / Gross Loss)
  - *Maximum Drawdown* (% & Nominal USD)
  - *Average Trade Expectancy* & *Payoff Ratio* (Rata-rata Win vs Loss)
  - *Estimasi Rasio Sharpe & Sortino* tahunan
  - *Status Leverage & Margin Call Counter*
- **Buku Besar Riwayat Trade Lengkap**:
  - Dukungan penayangan hingga 5.000+ trade tersimpan.
  - Paginasi institusional (25, 50, 100 baris atau Semua).
  - Filter cepat: `SEMUA`, `WIN`, dan `LOSS`.
  - Pencarian pair instan (contoh: BTC, PEPE, SOL).
  - Kolom lengkap: Waktu Closed, Durasi, Pair, Arah, Leverage, Entry/Exit Price, Realized PnL, Alasan Exit (TP/SL/Rotasi), dan Ekuitas Setelah Trade.

### 4. Visualisasi Kuantitatif Interaktif
- **Neural Network Visualizer**: Visualisasi feed-forward interaktif lapisan neural network inferensi sinyal (Input Layer Indikator $\rightarrow$ Hidden Layers Ekstraksi Fitur $\rightarrow$ Output Probabilitas Action Long/Short/Flat).
- **Three Market Core (3D WebGL)**: Representasi grafis sirkulasi likuiditas dan volatilitas pasar berbasis Three.js.

### 5. Hub Sinyal Publik & Copy-Trading API (v1)
- **Koneksi Bot Siap Pakai**: Ekspor sinyal order eksekusi langsung ke bot trading pribadi.
- **Otentikasi Kunci Publik**: Menggunakan Public Key default `pk_live_strategyarena_public_feed`.
- **Integrasi Multi-Platform**: Generator kode otomatis untuk bot Python (`aiohttp` / `requests`), WebSocket listener real-time, dan cURL REST.

---

## 🛠️ Panduan Menjalankan Sistem

### Opsi A: Menggunakan Docker (Rekomendasi untuk Produksi & Simulasi Penuh)

Seluruh sistem (Database PostgreSQL dan Aplikasi FastAPI + Frontend) dapat dijalankan dengan satu perintah:

```bash
# Jalankan container di latar belakang
docker compose up -d --build

# Periksa status container
docker compose ps

# Pantau log aktivitas simulasi real-time
docker compose logs -f app
```

Aplikasi dapat diakses langsung melalui browser di:
- **Terminal Web**: `http://localhost:8080/`
- **Port PostgreSQL**: `localhost:5433` (User: `arena`, Password: `arena`, Database: `arena`)

---

### Opsi B: Pengembangan Lokal (Local Development)

#### 1. Persiapan Database
Pastikan PostgreSQL berjalan lokal (atau gunakan container `arena-db` dari Docker):
```bash
docker compose up -d db
```

#### 2. Menjalankan Backend (FastAPI)
```bash
# Aktifkan virtual environment (opsional)
python -m venv venv
source venv/bin/activate  # Linux/macOS
# atau: .\venv\Scripts\activate  # Windows

# Pasang dependensi
pip install -r server/requirements.txt

# Ekspor environment variable
export DATABASE_URL="postgresql://arena:arena@localhost:5433/arena"

# Jalankan server FastAPI
python server/main.py
```

#### 3. Menjalankan Frontend (Vite Dev Server)
```bash
# Masuk ke direktori frontend
cd frontend

# Pasang paket dependensi
npm install

# Jalankan server pengembangan lokal (dengan hot-reload)
npm run dev

# Bangun aset produksi ke folder dist/
npm run build
```

---

## 🔌 Referensi REST & WebSocket API

| Endpoint | Metode | Parameter Query | Deskripsi |
| :--- | :---: | :--- | :--- |
| `/api/bootstrap` | `GET` | — | Memuat data awal: pasangan pair, daftar strategi, statistik server, dan status feed. |
| `/api/strategy/{sid}` | `GET` | `mode` (spot/futures), `hours` (1-2160), `limit` (max 10000) | Riwayat trade lengkap, ringkasan akun, aggregate count (win/loss), dan titik kurva ekuitas. |
| `/api/symbol/{symbol}` | `GET` | `limit` (1-500) | Data candlestick OHLCV historis 1m dari ring buffer. |
| `/api/v1/strategies` | `GET` | `mode` (spot/futures/all) | Ringkasan leaderboard performa semua strategi aktif. |
| `/api/v1/signals/positions`| `GET` | `strategy` (ID atau 'all'), `mode` (spot/futures/all) | Daftar posisi terbuka aktif saat ini untuk sinkronisasi portofolio copy-trade. |
| `/api/v1/signals/latest` | `GET` | `strategy`, `mode`, `action_type`, `limit`, `since_ts` | Riwayat sinyal eksekusi order terstruktur. |
| `/ws/signals` | `WS` | `api_key` | Real-time stream sinyal eksekusi order (JSON format). |
| `/ws` | `WS` | — | Stream real-time broadcast ekuitas, posisi, dan harga pasar per detik ke frontend. |
| `/api/reset` | `POST` | — | Reset seluruh data simulasi ke modal awal $10.000 (0 trade, 0 MC). |

---

## 🔒 Integritas Data & Transaksi
- **Zero-Drop Buffer**: Sistem persistensi PostgreSQL menggunakan buffer internal (`_new_trades` & `_new_signals`) yang menjamin tidak ada trade yang hilang meski operasi database mengalami beban tinggi.
- **Konsistensi Metrik Ledger**: Setiap perhitungan metrik performa (Win Rate, Total Trade, Profit Factor) disinkronkan secara atomik antara memori engine dan tabel buku besar PostgreSQL.
