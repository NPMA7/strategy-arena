# Strategy Arena — Terminal Kuantitatif & Mesin Simulasi Trading Real-Time

Platform terminal kuantitatif dan mesin simulasi *paper-trading* multi-strategi real-time berbasis **Python (FastAPI + AsyncPG)**, **PostgreSQL 17**, dan **Svelte 5 + Vite**. Sistem ini mengevaluasi dan mengadu ratusan algoritma kuantitatif secara simultan di 100 pasang aset kripto Binance serta 28 pasangan Forex & Logam Mulia MetaTrader 5 dengan umpan data pasar live (*tick-by-tick*).

Dirancang dengan standar visual **Institutional Craft** (Anti-AI-Slop, *functional depth*, dark theme konsisten, border presisi 1px, penempatan kolom waktu WIB di sisi kiri pair, tabel metrik densitas tinggi, serta bebas emoji generik).

> 🤖 **Mencari Mesin Copy-Trading Otomatis ke MetaTrader 5?**  
> Jika Anda ingin menyalin sinyal dari Strategy Arena langsung ke akun riil MetaTrader 5 (Headway, dsb.) secara otomatis dengan dukungan container MT5, rekonsiliasi watchdog, multi-strategy hedging, dan kontrol via bot Telegram (`/my-posisi`, `/posisi`, `/status`), gunakan repositori resmi:  
> 👉 [**https://github.com/NPMA7/sa-copytrade**](https://github.com/NPMA7/sa-copytrade)

---

## 🏛️ Arsitektur Sistem

```
┌────────────────────────────────────────────────────────────────────────┐
│                   Market Feeds (Binance & MT5 Bridge)                  │
│       • 100 Pair USDT Spot & Futures Streams (Binance WS/REST)         │
│       • 28 Pair Forex & Logam Mulia (MT5 Direct Bridge)        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Ring Buffer (250+ bar 1m)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                 Strategy Arena Engine (Triple Core)                    │
│  ┌────────────────────┐  ┌────────────────────┐  ┌──────────────────┐  │
│  │ Spot Engine        │  │ Futures Engine     │  │ Forex Engine     │  │
│  │ (39 Algoritma)     │  │ (53 Algoritma)     │  │ (88 Algoritma)   │  │
│  │ • Long-only Spot   │  │ • Long & Short Lev │  │ • Forex & Metals │  │
│  │ • Taker Fee 0.05%  │  │ • Funding Rate     │  │ • MT5 Real Spread│  │
│  └─────────┬──────────┘  └─────────┬──────────┘  └────────┬─────────┘  │
└────────────┼───────────────────────┼──────────────────────┼────────────┘
             ▼                       ▼                      ▼
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
│  • Posisi Aktif & Desk Pair dengan Kolom Waktu Open WIB di Kiri Pair   │
│  • Strategy Dossier & Modal Analisis Mendalam (Canvas Crosshair)       │
│  • Buku Besar Riwayat Trade Lengkap (Kolom Waktu Open & Closed)        │
│  • Visualisasi 3D WebGL Market Core & Feed-Forward Neural Network      │
│  • Hub Copy-Trading & Multi-Strategy Real-time Signals API             │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Fitur Utama

### 1. Triple-Core Real-Time Execution Engines
- **Spot Engine (39 Strategi)**: Fokus pada akumulasi spot, rotasi swing, dan *trend following* long-only tanpa risiko likuidasi leverage.
- **Futures Engine (53 Strategi)**: Mendukung posisi dua arah (**LONG & SHORT**) dengan leverage dinamis proporsional (5x hingga 20x) dan simulasi funding rate.
- **Forex & Metals Engine (88 Strategi)**:
  - Terintegrasi langsung dengan terminal MetaTrader 5 Real via RPyC Bridge.
  - Memperdagangkan 28 pair mayor, minor, dan logam mulia (**XAUUSD**, EURUSD, GBPUSD, USDJPY, dll.) dengan perhitungan pip dinamis dan spread floating riil.
  - Mendukung micro-lotting 0.01 dan mark-to-market live tick-by-tick.

### 2. Antarmuka Institusional Berbasis Svelte 5
- **Penempatan Kolom Waktu Open di Sisi Kiri Pair**:
  - Tabel **"POSISI AKTIF STRATEGI"**: `WAKTU OPEN | PAIR | ARAH | LOT | ENTRY | MARK | UPNL | RISIKO / MARGIN | STOP | TARGET`.
  - Tabel **"Pair yang sedang diperdagangkan"**: `WAKTU OPEN | STRATEGI | PAIR | ARAH | LOT | PIPS | ENTRY | MARK | UPNL | STOP`.
  - Tabel **"RIWAYAT TRADE LENGKAP"**: `WAKTU OPEN | WAKTU CLOSED | DURASI | PAIR | ARAH | LOT | ENTRY | EXIT | REALIZED PNL | ALASAN EXIT | EKUITAS`.
- **Format Jam Presisi WIB (Asia/Jakarta)**: Format 24 jam `HH:MM:SS WIB` terstandarisasi tanpa teks durasi relatif yang berantakan.
- **Multi-Kolom Sorting & Filter Kategori**: Urutkan strategi secara instan berdasarkan Ekuitas, Win Rate, Profit Factor, Total Trade, atau Drawdown.
- **Buku Besar Riwayat Trade Lengkap**: Dukungan ribuan trade tersimpan, paginasi instan (25/50/100 baris), filter `SEMUA/WIN/LOSS`, dan pencarian pair real-time.

### 3. Visualisasi Kuantitatif Interaktif
- **Neural Network Visualizer**: Visualisasi feed-forward interaktif lapisan neural network inferensi sinyal (Input Layer Indikator $\rightarrow$ Hidden Layers Ekstraksi Fitur $\rightarrow$ Output Probabilitas Action Long/Short/Flat).
- **Three Market Core (3D WebGL)**: Representasi grafis sirkulasi likuiditas dan volatilitas pasar berbasis Three.js.

### 4. Hub Sinyal Publik & Integrasi Copy-Trading (v1)
- **Mesin Eksekusi Copy-Trade Resmi**: Untuk menyalin sinyal trading secara langsung ke akun riil broker (MT5, akun Cent maupun Standard), silakan gunakan repositori pendamping resmi [**`sa-copytrade`**](https://github.com/NPMA7/sa-copytrade).
  - Repositori `sa-copytrade` menyediakan arsitektur bot daemon mandiri, hedging multi-strategi (`ALLOW_HEDGING`), remote command bot Telegram (`/my-posisi`, `/posisi`, `/status`, `/help`), smart fresh-trade reconciliation, dan tampilan GUI MT5 via browser (noVNC).
- **Dukungan Multi-Strategi Komprehensif**: Endpoint WebSocket `/ws/signals` dan REST `/api/v1/signals/positions` mendukung penyalinan beberapa strategi sekaligus via query koma (contoh: `?strategy=roc_momentum,gap_fill&mode=forex`).
- **Otentikasi Kunci Publik**: Menggunakan Public Key default `pk_live_strategyarena_public_feed`.
- **Generator Kode Terintegrasi**: Panduan dan template bot siap pakai untuk Python (`aiohttp` / `websockets`), cURL, dan integrasi MetaTrader 5.

---

## 🛠️ Panduan Menjalankan Sistem

### Opsi A: Menggunakan Docker (Rekomendasi Produksi)

Seluruh sistem (Database PostgreSQL, MT5 Bridge, dan Aplikasi FastAPI + Frontend) dapat dijalankan dengan satu perintah:

```bash
# Jalankan seluruh service di latar belakang
docker compose up -d --build

# Periksa status container
docker compose ps

# Pantau log aktivitas simulasi real-time
docker compose logs -f app
```

Aplikasi dapat diakses langsung melalui browser di:
- **Terminal Web**: `http://localhost:8080/` (atau port server yang dikonfigurasikan)
- **Port PostgreSQL**: `localhost:5433` (User: `arena`, Password: `arena`, Database: `arena`)

---

### Opsi B: Pengembangan Lokal (Local Development)

#### 1. Persiapan Database
```bash
docker compose up -d db
```

#### 2. Menjalankan Backend (FastAPI)
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# atau: .\venv\Scripts\activate  # Windows

pip install -r server/requirements.txt
export DATABASE_URL="postgresql://arena:arena@localhost:5433/arena"

python server/main.py
```

#### 3. Menjalankan Frontend (Vite Dev Server)
```bash
cd frontend
npm install
npm run dev

# Kompilasi aset produksi ke folder dist/
npm run build
```

---

## 🔌 Referensi REST & WebSocket API

| Endpoint | Metode | Parameter Query | Deskripsi |
| :--- | :---: | :--- | :--- |
| `/api/bootstrap` | `GET` | — | Memuat data awal: pasangan pair, daftar strategi, statistik server, dan status feed. |
| `/api/strategy/{sid}` | `GET` | `mode` (spot/futures/forex), `hours` (1-2160) | Ringkasan akun, aggregate count (win/loss), dan titik kurva ekuitas. |
| `/api/strategy/{sid}/trades` | `GET` | `mode`, `page`, `limit` (default 50), `filter` (all/win/loss), `search` | Riwayat transaksi terpaginasi dari server PostgreSQL dengan filter dan pencarian instan. |
| `/api/symbol/{symbol}` | `GET` | `limit` (1-500) | Data candlestick OHLCV historis 1m dari ring buffer. |
| `/api/v1/signals/strategies` | `GET` | `mode`, `api_key` | Peringkat dan performa semua strategi aktif. |
| `/api/v1/signals/positions` | `GET` | `strategy` (ID / koma / 'all'), `mode`, `api_key` | Daftar posisi terbuka aktif saat ini untuk sinkronisasi portofolio copy-trade. |
| `/api/v1/signals/feed` | `GET` | `strategy`, `mode`, `limit`, `action`, `api_key` | Riwayat sinyal eksekusi order terstruktur dari database. |
| `/ws/signals` | `WS` | `strategy`, `mode`, `api_key` | Real-time WebSocket stream sinyal eksekusi order instan. |
| `/ws` | `WS` | — | Stream real-time broadcast ekuitas, posisi, dan harga pasar per detik ke antarmuka web. |

---

## 🔒 Integritas Data & Transaksi
- **Zero-Drop Buffer**: Sistem persistensi PostgreSQL menggunakan buffer internal (`_new_trades` & `_new_signals`) yang menjamin tidak ada trade yang hilang meski operasi database mengalami beban tinggi.
- **Konsistensi Metrik Ledger**: Setiap perhitungan metrik performa (Win Rate, Total Trade, Profit Factor) disinkronkan secara atomik antara memori engine dan tabel buku besar PostgreSQL.
