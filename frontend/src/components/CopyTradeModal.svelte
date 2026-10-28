<script>
  import { arena } from '../lib/store.svelte.js';

  let selectedStrategy = $state(arena.selectedStrategyId || 'all');
  let selectedMode = $state(arena.mode);
  let activeTab = $state('python'); // 'python', 'ws', 'curl', 'json'
  let copyFeedback = $state('');

  let accounts = $derived(
    selectedMode === 'spot'
      ? arena.spot.accounts
      : selectedMode === 'futures'
      ? arena.futures.accounts
      : selectedMode === 'forex'
      ? arena.forex.accounts
      : [...arena.forex.accounts, ...arena.futures.accounts, ...arena.spot.accounts]
  );

  let host = $derived(window.location.host);
  let protoWs = $derived(window.location.protocol === 'https:' ? 'wss' : 'ws');
  let protoHttp = $derived(window.location.protocol);

  let wsUrl = $derived(
    `${protoWs}://${host}/ws/signals?strategy=${selectedStrategy}&mode=${selectedMode}&api_key=${arena.activeApiKey}`
  );

  let pythonCode = $derived(
`import asyncio, websockets, json

API_KEY = "${arena.activeApiKey}"
WS_URL = "${wsUrl}"

async def copy_trading_client():
    async with websockets.connect(WS_URL) as ws:
        print(f"[+] Terhubung ke Strategy Arena Signal Stream (${selectedMode.toUpperCase()})!")
        while True:
            msg = await ws.recv()
            event = json.loads(msg)
            if event.get("type") == "signal":
                sig = event["signal"]
                print(f"[*] SIGNAL: {sig['action']} {sig['symbol']} @ {sig['price']} | TP: {sig.get('take_profit')} | SL: {sig.get('stop_loss')}")
                # Eksekusi order ke Binance/Bybit/Exchange akun Anda

asyncio.run(copy_trading_client())`
  );

  let curlCode = $derived(
`# 1. Cek posisi aktif strategi terpilih:
curl -s "${protoHttp}//${host}/api/v1/signals/positions?strategy=${selectedStrategy}&mode=${selectedMode}&api_key=${arena.activeApiKey}"

# 2. Riwayat sinyal eksekusi terbaru:
curl -s "${protoHttp}//${host}/api/v1/signals/feed?strategy=${selectedStrategy}&mode=${selectedMode}&limit=20&api_key=${arena.activeApiKey}"

# 3. Peringkat performa strategi:
curl -s "${protoHttp}//${host}/api/v1/signals/strategies?mode=${selectedMode}&api_key=${arena.activeApiKey}"`
  );

  let wsCode = $derived(
`wscat -c "${wsUrl}"`
  );

  let jsonSchema = $derived(
`{
  "type": "signal",
  "signal": {
    "strategy": "${selectedStrategy === 'all' ? 'turtle' : selectedStrategy}",
    "mode": "${selectedMode}",
    "symbol": "BTCUSDT",
    "action": "BUY",
    "price": 68420.5,
    "leverage": ${selectedMode === 'futures' ? 10 : 1},
    "margin_usd": 200.0,
    "take_profit": 71840.0,
    "stop_loss": 66710.0,
    "timestamp": 1793107500000
  }
}`
  );

  async function copyToClipboard(text, label) {
    try {
      await navigator.clipboard.writeText(text);
      copyFeedback = `${label} berhasil disalin!`;
      setTimeout(() => (copyFeedback = ''), 2500);
    } catch {
      copyFeedback = 'Gagal menyalin.';
    }
  }
</script>

{#if arena.copyTradeModalOpen}
  <div class="modal-root" role="dialog" aria-modal="true">
    <button
      class="modal-backdrop"
      type="button"
      aria-label="Tutup modal"
      onclick={() => (arena.copyTradeModalOpen = false)}
    ></button>
    <div class="modal-card">
      <div class="modal-header">
        <div class="modal-title-box">
          <div class="m-icon">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
            </svg>
          </div>
          <div>
            <h2 class="font-display">Copy-Trade Signal Stream & Public API</h2>
            <p>Salin sinyal order eksekusi (Open, TP, SL, Exit) secara real-time ke bot atau exchange pribadi.</p>
          </div>
        </div>
        <button class="m-close" onclick={() => (arena.copyTradeModalOpen = false)}>×</button>
      </div>

      <!-- Public Key Box -->
      <div class="key-box">
        <div class="key-label">
          <span>PUBLIC FEED API KEY</span>
          <span class="rate-limit">Rate limit: 60 req/min · No Secret Required</span>
        </div>
        <div class="key-input-row">
          <input type="text" readonly value={arena.activeApiKey} class="mono" />
          <button
            class="btn-copy-key"
            onclick={() => copyToClipboard(arena.activeApiKey, 'API Key')}
          >
            Salin Kunci
          </button>
        </div>
      </div>

      <!-- Strategy & Mode Selectors -->
      <div class="filter-row">
        <div class="filter-col">
          <label for="selMode">PILIH PASAR:</label>
          <select id="selMode" bind:value={selectedMode}>
            <option value="futures">Crypto Futures Arena (50++ Strategi)</option>
            <option value="spot">Crypto Spot Arena (35++ Strategi)</option>
            <option value="forex">Forex & Metals Arena (22++ Strategi)</option>
            <option value="all">Semua Pasar (Cross-Market Stream)</option>
          </select>
        </div>

        <div class="filter-col flex-1">
          <label for="selStrat">PILIH STRATEGI:</label>
          <select id="selStrat" bind:value={selectedStrategy}>
            <option value="all">Semua Strategi (Full Stream Feed)</option>
            {#each accounts as a}
              <option value={a.id}>
                {a.name || a.id} ({a.equity >= 10000 ? '+' : ''}{((a.equity / 10000 - 1) * 100).toFixed(1)}%)
              </option>
            {/each}
          </select>
        </div>
      </div>

      <!-- Snippet Tabs -->
      <div class="snippet-section">
        <div class="snippet-tabs">
          <button
            class="s-tab {activeTab === 'python' ? 'active' : ''}"
            onclick={() => (activeTab = 'python')}
          >
            Python Bot Client
          </button>
          <button
            class="s-tab {activeTab === 'ws' ? 'active' : ''}"
            onclick={() => (activeTab = 'ws')}
          >
            WebSocket CLI
          </button>
          <button
            class="s-tab {activeTab === 'curl' ? 'active' : ''}"
            onclick={() => (activeTab = 'curl')}
          >
            cURL / REST
          </button>
          <button
            class="s-tab {activeTab === 'json' ? 'active' : ''}"
            onclick={() => (activeTab = 'json')}
          >
            JSON Format
          </button>
        </div>

        <div class="snippet-box">
          {#if activeTab === 'python'}
            <pre class="mono"><code>{pythonCode}</code></pre>
          {:else if activeTab === 'ws'}
            <pre class="mono"><code>{wsCode}</code></pre>
          {:else if activeTab === 'curl'}
            <pre class="mono"><code>{curlCode}</code></pre>
          {:else}
            <pre class="mono"><code>{jsonSchema}</code></pre>
          {/if}

          <div class="snippet-actions">
            {#if copyFeedback}
              <span class="copy-fb num">{copyFeedback}</span>
            {/if}
            <button
              class="btn-copy-code"
              onclick={() => {
                const code =
                  activeTab === 'python'
                    ? pythonCode
                    : activeTab === 'ws'
                    ? wsCode
                    : activeTab === 'curl'
                    ? curlCode
                    : jsonSchema;
                copyToClipboard(code, 'Kode Cuplikan');
              }}
            >
              <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
              </svg>
              <span>Salin Kode</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  .modal-root {
    position: fixed;
    inset: 0;
    z-index: 100;
    display: grid;
    place-items: center;
    padding: 20px;
  }

  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.8);
    backdrop-filter: blur(5px);
    border: none;
    cursor: default;
    width: 100%;
    height: 100%;
  }

  .modal-card {
    position: relative;
    z-index: 101;
    background-color: var(--bg-surface);
    border: 1px solid var(--border-muted);
    border-radius: 12px;
    width: 100%;
    max-width: 760px;
    max-height: 90vh;
    overflow-y: auto;
    padding: 24px;
    display: flex;
    flex-direction: column;
    gap: 16px;
    box-shadow: var(--shadow-lg);
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    border-bottom: 1px solid var(--border-subtle);
    padding-bottom: 14px;
  }

  .modal-title-box {
    display: flex;
    gap: 12px;
    align-items: center;
  }

  .m-icon {
    font-size: 26px;
    color: var(--color-amber);
  }

  .modal-title-box h2 {
    font-size: 17px;
    font-weight: 700;
    color: var(--fg-primary);
  }

  .modal-title-box p {
    font-size: 12px;
    color: var(--fg-muted);
    margin-top: 2px;
  }

  .m-close {
    font-size: 24px;
    color: var(--fg-muted);
    line-height: 1;
  }
  .m-close:hover {
    color: var(--fg-primary);
  }

  .key-box {
    background-color: var(--bg-base);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .key-label {
    display: flex;
    justify-content: space-between;
    font-size: 10.5px;
    font-weight: 700;
    color: var(--fg-muted);
  }

  .rate-limit {
    font-weight: 400;
    color: var(--fg-dim);
  }

  .key-input-row {
    display: flex;
    gap: 8px;
  }

  .key-input-row input {
    flex: 1;
    background-color: var(--bg-input);
    border: 1px solid var(--border-subtle);
    border-radius: 6px;
    padding: 6px 10px;
    color: var(--color-amber);
    font-size: 12px;
    font-weight: 600;
  }

  .btn-copy-key {
    padding: 6px 14px;
    background: var(--bg-surface-elevated);
    border: 1px solid var(--border-muted);
    border-radius: 6px;
    color: var(--fg-primary);
    font-size: 12px;
    font-weight: 600;
  }
  .btn-copy-key:hover {
    background: var(--bg-surface-hover);
  }

  .filter-row {
    display: flex;
    gap: 12px;
  }

  .filter-col {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .flex-1 {
    flex: 1;
  }

  .filter-col label {
    font-size: 10px;
    font-weight: 700;
    color: var(--fg-muted);
  }

  .filter-col select {
    background-color: var(--bg-base);
    border: 1px solid var(--border-subtle);
    border-radius: 6px;
    padding: 7px 10px;
    color: var(--fg-primary);
    font-size: 12px;
    outline: none;
  }

  .snippet-section {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .snippet-tabs {
    display: flex;
    gap: 4px;
    border-bottom: 1px solid var(--border-subtle);
  }

  .s-tab {
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 600;
    color: var(--fg-muted);
    border-bottom: 2px solid transparent;
  }

  .s-tab.active {
    color: var(--color-amber);
    border-bottom-color: var(--color-amber);
  }

  .snippet-box {
    position: relative;
    background-color: var(--bg-base);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    padding: 14px;
    max-height: 260px;
    overflow-y: auto;
  }

  .snippet-box pre {
    margin: 0;
    font-size: 11px;
    line-height: 1.5;
    color: #e2e8f0;
    white-space: pre-wrap;
    word-break: break-all;
  }

  .snippet-actions {
    display: flex;
    justify-content: flex-end;
    align-items: center;
    gap: 12px;
    margin-top: 10px;
  }

  .copy-fb {
    font-size: 11px;
    color: var(--color-up);
    font-weight: 600;
  }

  .btn-copy-code {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 6px 14px;
    background-color: var(--color-amber-bg);
    border: 1px solid var(--border-amber);
    color: var(--color-amber);
    border-radius: 6px;
    font-size: 12px;
    font-weight: 600;
    cursor: pointer;
  }

  .btn-copy-code:hover {
    background-color: rgba(245, 158, 11, 0.2);
  }
</style>
