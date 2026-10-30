<script>
  import { arena } from '../lib/store.svelte.js';

  let events = $derived(arena.activeEvents);
</script>

<section class="panel logs-panel">
  <div class="phead">
    <h2>Log realtime</h2>
    <span class="sub muted">event bar tertutup</span>
  </div>

  <div class="feed-wrap">
    {#if events.length === 0}
      <div class="empty-feed">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
          <line x1="16" y1="13" x2="8" y2="13"></line>
          <line x1="16" y1="17" x2="8" y2="17"></line>
        </svg>
        <span>Menunggu eksekusi order berikutnya…</span>
      </div>
    {:else}
      <div class="feed-list">
        {#each [...events].reverse() as e, i (e.ts + '_' + (e.symbol || '') + '_' + (e.kind || '') + '_' + i)}
          {@const timeStr = new Date(e.ts).toLocaleTimeString('id-ID', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
          {@const isEntry = (e.kind || '').includes('entry') || (e.message || '').includes('OPEN')}
          {@const isExit = (e.kind || '').includes('exit') || (e.message || '').includes('CLOSE')}
          {@const isMC = (e.kind || '').includes('refill') || (e.message || '').includes('REFILL') || (e.message || '').includes('MC')}
          <div class="ev-row">
            <span class="ev-t mono">{timeStr}</span>
            <span class="ev-strat">{(e.strats || []).join(', ') || 'arena'}</span>
            <span class="ev-badge {isMC ? 'b-mc' : isEntry ? 'b-entry' : 'b-exit'}">
              {isMC ? 'REFILL' : isEntry ? 'ENTRY' : 'EXIT'}
            </span>
            <span class="ev-msg mono">{e.message}</span>
          </div>
        {/each}
      </div>
    {/if}
  </div>
</section>

<style>
  .logs-panel {
    background: #090d14;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    display: flex;
    flex-direction: column;
    height: 100%;
    min-height: 280px;
    overflow: hidden;
  }

  .phead {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 6px 12px;
    flex-wrap: wrap;
    padding: 10px 14px;
    background: #06090e;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    flex-shrink: 0;
  }

  .phead h2 {
    font-size: 13.5px;
    font-weight: 700;
    color: #e2e8f0;
    letter-spacing: -0.01em;
  }

  .sub {
    font-size: 10.5px;
    color: #64748b;
  }

  .feed-wrap {
    flex: 1 1 auto;
    min-height: 200px;
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
    scrollbar-gutter: stable;
    padding: 8px 10px;
    background: #06090e;
  }

  .feed-list {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .ev-row {
    display: flex;
    align-items: baseline;
    gap: 8px;
    padding: 5px 8px;
    background: #0c1018;
    border: 1px solid rgba(255, 255, 255, 0.04);
    border-radius: 4px;
    font-size: 11px;
    line-height: 1.4;
  }

  .ev-t {
    font-size: 10px;
    color: #64748b;
    white-space: nowrap;
    min-width: 52px;
  }

  .ev-strat {
    font-size: 11px;
    font-weight: 600;
    color: #38bdf8;
    white-space: nowrap;
    min-width: 100px;
    max-width: 160px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .ev-badge {
    font-size: 9px;
    font-weight: 700;
    padding: 1px 4px;
    border-radius: 3px;
    white-space: nowrap;
  }

  .b-entry {
    background: rgba(16, 185, 129, 0.15);
    color: #10b981;
    border: 1px solid rgba(16, 185, 129, 0.3);
  }

  .b-exit {
    background: rgba(245, 158, 11, 0.15);
    color: #f59e0b;
    border: 1px solid rgba(245, 158, 11, 0.3);
  }

  .b-mc {
    background: rgba(244, 63, 94, 0.2);
    color: #f43f5e;
    border: 1px solid rgba(244, 63, 94, 0.4);
  }

  .ev-msg {
    font-size: 10.5px;
    color: #cbd5e1;
    flex: 1;
    word-break: break-all;
  }

  .empty-feed {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 40px;
    color: #64748b;
    font-size: 12px;
  }

  @media (max-width: 480px) {
    .logs-panel {
      min-height: 260px;
    }
    .phead {
      padding: 8px 10px;
      gap: 4px;
    }
    .feed-wrap {
      min-height: 180px;
      padding: 6px 8px;
    }
    .ev-row {
      flex-wrap: wrap;
      gap: 4px;
      padding: 6px 8px;
    }
    .ev-strat {
      min-width: 0;
      max-width: 120px;
    }
    .ev-msg {
      width: 100%;
      flex-basis: 100%;
    }
  }
</style>
