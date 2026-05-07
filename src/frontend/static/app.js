(() => {
  const FALLBACK_POLL_INTERVAL_MS = 30_000;
  const MAX_RECONNECT_DELAY_MS = 5_000;
  const PERFORMANCE_POLL_INTERVAL_MS = 60_000;
  const BOT_ACTIVITY_POLL_INTERVAL_MS = 30_000;
  const TRADE_HISTORY_POLL_INTERVAL_MS = 60_000;

  const state = {
    socket: null,
    reconnectTimer: null,
    fallbackTimer: null,
    reconnectAttempt: 0,
    lastSnapshot: null,
    intentionalClose: false,
    positions: [],
    filterSymbol: "",
    filterDirection: "",
  };

  const elements = {
    connectionStatus: document.getElementById("connection-status"),
    lastUpdate: document.getElementById("last-update"),
    analysisBiasDirection: document.getElementById("analysis-bias-direction"),
    analysisBiasConfidence: document.getElementById("analysis-bias-confidence"),
    analysisBiasReason: document.getElementById("analysis-bias-reason"),
    analysisOpportunities: document.getElementById("analysis-opportunities"),
    banner: document.getElementById("banner"),
    bannerTitle: document.getElementById("banner-title"),
    bannerMessage: document.getElementById("banner-message"),
    summaryExposure: document.getElementById("summary-exposure"),
    summaryMargin: document.getElementById("summary-margin"),
    summaryPnl: document.getElementById("summary-pnl"),
    snapshotStatus: document.getElementById("snapshot-status"),
    positionsBody: document.getElementById("positions-body"),
    performanceStatus: document.getElementById("performance-status"),
    perfTotalTrades: document.getElementById("perf-total-trades"),
    perfWinRate: document.getElementById("perf-win-rate"),
    perfTotalPnl: document.getElementById("perf-total-pnl"),
    perfAvgRrr: document.getElementById("perf-avg-rrr"),
    perfMaxDrawdown: document.getElementById("perf-max-drawdown"),
    perfProfitFactor: document.getElementById("perf-profit-factor"),
    perfBySymbolBody: document.getElementById("perf-by-symbol-body"),
    perfByTimeframeBody: document.getElementById("perf-by-timeframe-body"),
    botStatusIndicator: document.getElementById("bot-status-indicator"),
    botStatusDot: document.getElementById("bot-status-dot"),
    botStatusText: document.getElementById("bot-status-text"),
    botStatusTime: document.getElementById("bot-status-time"),
    filterSymbol: document.getElementById("filter-symbol"),
    directionButtons: Array.from(document.querySelectorAll(".dir-btn")),
    tradeHistoryBody: document.getElementById("trade-history-body"),
  };

  const moneyFormatter = new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

  const numberFormatter = new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 8,
  });

  const priceFormatter = new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 4,
    maximumFractionDigits: 4,
  });

  const percentFormatter = new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
    signDisplay: "always",
  });

  const dateTimeFormatter = new Intl.DateTimeFormat("pt-BR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  const timeFormatter = new Intl.DateTimeFormat("pt-BR", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  function formatDateTimeToLocal(isoString) {
    if (!isoString) {
      return "—";
    }
    try {
      const date = new Date(isoString);
      if (isNaN(date.getTime())) {
        return isoString;
      }
      return dateTimeFormatter.format(date);
    } catch (_) {
      return isoString;
    }
  }

  function formatClockTime(isoString) {
    if (!isoString) {
      return "—";
    }
    try {
      const date = new Date(isoString);
      if (isNaN(date.getTime())) {
        return "—";
      }
      return timeFormatter.format(date);
    } catch (_) {
      return "—";
    }
  }

  function formatMoney(value) {
    if (value === null || value === undefined || value === "—") {
      return "—";
    }
    return moneyFormatter.format(Number(value));
  }

  function formatPrice(value) {
    if (value === null || value === undefined || value === "—") {
      return "—";
    }
    return priceFormatter.format(Number(value));
  }

  function formatPercent(value) {
    if (value === null || value === undefined || value === "—") {
      return "—";
    }
    return `${percentFormatter.format(Number(value))}%`;
  }

  function getRoiClass(value) {
    if (value === null || value === undefined || value === "—") {
      return "";
    }
    return Number(value) >= 0 ? "text-positive" : "text-negative";
  }

  function formatNumber(value) {
    if (value === null || value === undefined || value === "—") {
      return "—";
    }
    return numberFormatter.format(Number(value));
  }

  function setStatus(status) {
    elements.connectionStatus.textContent = status;
    elements.connectionStatus.className = `status-pill status-pill--${status}`;
    elements.snapshotStatus.textContent = status;
    elements.snapshotStatus.className = `snapshot-status snapshot-status--${status}`;
  }

  function setBanner(banner) {
    if (!banner || !banner.visible) {
      elements.banner.classList.add("banner--hidden");
      elements.bannerTitle.textContent = "";
      elements.bannerMessage.textContent = "";
      return;
    }

    elements.banner.classList.remove("banner--hidden");
    elements.banner.dataset.level = banner.level;
    elements.bannerTitle.textContent = banner.title;
    elements.bannerMessage.textContent = banner.message;
  }

  function startFallbackPolling() {
    if (state.fallbackTimer) {
      return;
    }

    fetchSnapshotViaRest();
    state.fallbackTimer = window.setInterval(fetchSnapshotViaRest, FALLBACK_POLL_INTERVAL_MS);
  }

  function stopFallbackPolling() {
    if (!state.fallbackTimer) {
      return;
    }

    window.clearInterval(state.fallbackTimer);
    state.fallbackTimer = null;
  }

  async function fetchSnapshotViaRest() {
    try {
      const response = await fetch("/positions", { cache: "no-store" });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const snapshot = await response.json();
      renderSnapshot(snapshot);
    } catch (_) {
      setStatus("offline");
      setBanner({
        visible: true,
        level: "critical",
        title: "Falha de conexão",
        message: "Não foi possível atualizar o painel. Tentando reconectar...",
      });
    }
  }

  function renderSummary(summary) {
    elements.summaryExposure.textContent = formatMoney(summary.total_exposure_usdt);
    elements.summaryMargin.textContent = formatMoney(summary.total_margin_used_usdt);
    elements.summaryPnl.textContent = formatMoney(summary.total_unrealized_pnl_usdt);
    elements.lastUpdate.textContent = `Atualizado em ${formatDateTimeToLocal(summary.last_update_at)}`;
  }

  function renderMarketAnalysis(analysis) {
    if (!analysis) {
      elements.analysisBiasDirection.textContent = "—";
      elements.analysisBiasConfidence.textContent = "—";
      elements.analysisBiasReason.textContent = "Aguardando dados para calcular bias e oportunidades.";
      elements.analysisOpportunities.innerHTML = "<li>Nenhuma oportunidade detectada.</li>";
      return;
    }

    elements.analysisBiasDirection.textContent = analysis.bias.direction;
    elements.analysisBiasConfidence.textContent = analysis.bias.confidence;
    elements.analysisBiasReason.textContent = analysis.bias.reason;
    elements.analysisOpportunities.innerHTML = renderOpportunities(analysis.opportunities);
  }

  function renderOpportunities(opportunities) {
    if (!Array.isArray(opportunities) || opportunities.length === 0) {
      return `<li>Nenhuma oportunidade detectada.</li>`;
    }

    return opportunities
      .map(
        (opportunity) => `
          <li>
            <strong>${opportunity.action}</strong> ${opportunity.direction}
            ${opportunity.symbol ? `em ${opportunity.symbol}` : ""}
            <div class="opportunity-rationale">${opportunity.rationale}</div>
          </li>
        `,
      )
      .join("");
  }

  function resetPositionFilters() {
    state.filterSymbol = "";
    state.filterDirection = "";
    if (elements.filterSymbol) {
      elements.filterSymbol.value = "";
    }
    elements.directionButtons.forEach((button) => {
      button.classList.toggle("active", button.dataset.dir === "");
    });
  }

  function populateSymbolFilter(positions) {
    if (!elements.filterSymbol) {
      return;
    }
    const symbols = [...new Set(positions.map((position) => position.symbol))].sort();
    const options = [
      '<option value="">Todos os símbolos</option>',
      ...symbols.map((symbol) => `<option value="${symbol}">${symbol}</option>`),
    ];
    elements.filterSymbol.innerHTML = options.join("");
    elements.filterSymbol.value = state.filterSymbol;
  }

  function renderPositionsEmptyRow(message) {
    elements.positionsBody.innerHTML = `
      <tr class="empty-row">
        <td colspan="14">${message}</td>
      </tr>
    `;
  }

  function renderPositionRows(positions) {
    elements.positionsBody.innerHTML = positions
      .map(
        (position) => `
          <tr>
            <td>${position.symbol}</td>
            <td>${position.side}</td>
            <td>${formatNumber(position.quantity)}</td>
            <td>${position.leverage}</td>
            <td>${formatMoney(position.entry_price)}</td>
            <td class="${position.sl_price == null ? "sl-missing" : ""}">${formatPrice(position.sl_price)}</td>
            <td>${formatPrice(position.tp_price)}</td>
            <td>${formatMoney(position.mark_price)}</td>
            <td>${formatMoney(position.unrealized_pnl_usdt)}</td>
            <td>${formatMoney(position.margin_used_usdt)}</td>
            <td>${formatNumber(position.position_size_usdt)}</td>
            <td class="${getRoiClass(position.roi_adjusted_pct)}">${formatPercent(position.roi_adjusted_pct)}</td>
            <td>${formatMoney(position.liquidation_price)}</td>
            <td>${position.updated_at}</td>
          </tr>
        `,
      )
      .join("");
  }

  function applyPositionFilters() {
    if (!Array.isArray(state.positions) || state.positions.length === 0) {
      renderPositionsEmptyRow("Nenhuma posição aberta no momento.");
      return;
    }

    const filteredPositions = state.positions.filter((position) => {
      const symbolMatches = !state.filterSymbol || position.symbol === state.filterSymbol;
      const directionMatches = !state.filterDirection ||
        String(position.side || "").toLowerCase() === state.filterDirection;
      return symbolMatches && directionMatches;
    });

    if (filteredPositions.length === 0) {
      renderPositionsEmptyRow("Nenhuma posição encontrada para os filtros selecionados.");
      return;
    }

    renderPositionRows(filteredPositions);
  }

  function bindPositionFilterEvents() {
    if (elements.filterSymbol) {
      elements.filterSymbol.addEventListener("change", (event) => {
        state.filterSymbol = event.target.value;
        applyPositionFilters();
      });
    }

    elements.directionButtons.forEach((button) => {
      button.addEventListener("click", () => {
        state.filterDirection = button.dataset.dir || "";
        elements.directionButtons.forEach((innerButton) => {
          innerButton.classList.toggle("active", innerButton === button);
        });
        applyPositionFilters();
      });
    });
  }

  function renderPositions(positions) {
    state.positions = Array.isArray(positions) ? positions : [];
    resetPositionFilters();
    populateSymbolFilter(state.positions);
    applyPositionFilters();
  }

  function renderBotStatus(data) {
    const active = data?.status === "active";
    elements.botStatusIndicator.classList.toggle("bot-status-badge--active", active);
    elements.botStatusIndicator.classList.toggle("bot-status-badge--inactive", !active);
    elements.botStatusText.textContent = active ? "ATIVO" : "INATIVO";

    const latestCycle = formatClockTime(data?.last_activity_at);
    elements.botStatusTime.textContent = `Último ciclo: ${latestCycle}`;
    elements.botStatusIndicator.title = `Último ciclo detectado às ${latestCycle}`;
  }

  function renderTradeHistory(trades) {
    if (!Array.isArray(trades) || trades.length === 0) {
      elements.tradeHistoryBody.innerHTML = `
        <tr class="empty-row">
          <td colspan="10">Nenhum trade fechado encontrado.</td>
        </tr>
      `;
      return;
    }

    elements.tradeHistoryBody.innerHTML = trades
      .map((trade) => {
        const pnlClass =
          trade.pnl_usdt == null ? "" : Number(trade.pnl_usdt) >= 0 ? "metric-positive" : "metric-negative";
        const pnlValue = trade.pnl_usdt == null ? "—" : formatMoney(trade.pnl_usdt);
        return `
          <tr>
            <td>${trade.symbol ?? "—"}</td>
            <td>${trade.timeframe ?? "—"}</td>
            <td>${String(trade.direction ?? "—").toUpperCase()}</td>
            <td>${formatPrice(trade.entry_price)}</td>
            <td>${formatPrice(trade.exit_price)}</td>
            <td>${formatPrice(trade.stop_loss)}</td>
            <td>${formatPrice(trade.take_profit)}</td>
            <td class="${pnlClass}">${pnlValue}</td>
            <td>${trade.status ?? "—"}</td>
            <td>${formatDateTimeToLocal(trade.closed_at)}</td>
          </tr>
        `;
      })
      .join("");
  }

  async function fetchBotActivity() {
    try {
      const response = await fetch("/bot-activity", { cache: "no-store" });
      if (!response.ok) {
        return;
      }
      const payload = await response.json();
      renderBotStatus(payload);
    } catch (_) {
      // silencioso — painel de posições não é afetado
    }
  }

  async function fetchTradeHistory() {
    try {
      const response = await fetch("/trades/history", { cache: "no-store" });
      if (!response.ok) {
        return;
      }
      const payload = await response.json();
      renderTradeHistory(payload.trades);
    } catch (_) {
      // silencioso — painel de posições não é afetado
    }
  }

  function renderSnapshot(snapshot) {
    state.lastSnapshot = snapshot;
    renderPositions(snapshot.positions);
    renderSummary(snapshot.summary);
    renderMarketAnalysis(snapshot.analysis);
    setStatus(snapshot.status);
    setBanner(snapshot.banner);
  }

  function scheduleReconnect() {
    if (state.reconnectTimer) {
      window.clearTimeout(state.reconnectTimer);
    }

    const delay = Math.min(MAX_RECONNECT_DELAY_MS, 500 * 2 ** state.reconnectAttempt);
    state.reconnectTimer = window.setTimeout(() => {
      state.reconnectAttempt += 1;
      connect();
    }, delay);
  }

  function connect() {
    if (state.socket) {
      state.intentionalClose = true;
      state.socket.close();
    }

    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const socketUrl = `${protocol}//${window.location.host}/ws/positions`;
    const socket = new WebSocket(socketUrl);
    state.socket = socket;
    state.intentionalClose = false;

    socket.addEventListener("open", () => {
      state.reconnectAttempt = 0;
      setStatus("online");
      setBanner({ visible: false });
      stopFallbackPolling();
    });

    socket.addEventListener("message", (event) => {
      const snapshot = JSON.parse(event.data);
      renderSnapshot(snapshot);
    });

    socket.addEventListener("close", () => {
      setStatus("offline");
      setBanner({
        visible: true,
        level: "critical",
        title: "Offline",
        message: "Sem conexão com o servidor. Tentando reconectar...",
      });

      startFallbackPolling();

      if (state.intentionalClose) {
        state.intentionalClose = false;
        return;
      }

      scheduleReconnect();
    });

    socket.addEventListener("error", () => {
      if (state.socket?.readyState !== WebSocket.OPEN) {
        setStatus("offline");
      }
    });
  }

  function renderGroupTable(tbodyEl, data) {
    const entries = Object.entries(data || {});
    if (entries.length === 0) {
      tbodyEl.innerHTML = `<tr class="empty-row"><td colspan="7">Sem trades fechados.</td></tr>`;
      return;
    }
    tbodyEl.innerHTML = entries
      .map(
        ([key, m]) => `
          <tr>
            <td>${key}</td>
            <td>${m.total_trades}</td>
            <td>${formatPercent(m.win_rate_pct)}</td>
            <td class="${m.total_pnl_usdt >= 0 ? "metric-positive" : "metric-negative"}">${formatMoney(m.total_pnl_usdt)}</td>
            <td>${m.avg_rrr.toFixed(2)}</td>
            <td>${formatMoney(m.max_drawdown_usdt)}</td>
            <td>${m.profit_factor.toFixed(2)}</td>
          </tr>
        `,
      )
      .join("");
  }

  function renderPerformance(global, bySymbol, byTimeframe) {
    elements.performanceStatus.textContent = "atualizado";
    elements.perfTotalTrades.textContent = global.total_trades ?? "—";
    elements.perfWinRate.textContent = formatPercent(global.win_rate_pct);
    elements.perfTotalPnl.textContent = formatMoney(global.total_pnl_usdt);
    elements.perfAvgRrr.textContent = global.avg_rrr != null ? global.avg_rrr.toFixed(2) : "—";
    elements.perfMaxDrawdown.textContent = formatMoney(global.max_drawdown_usdt);
    elements.perfProfitFactor.textContent =
      global.profit_factor != null ? global.profit_factor.toFixed(2) : "—";
    renderGroupTable(elements.perfBySymbolBody, bySymbol);
    renderGroupTable(elements.perfByTimeframeBody, byTimeframe);
  }

  async function fetchPerformance() {
    try {
      const [globalRes, bySymbolRes, byTimeframeRes] = await Promise.all([
        fetch("/performance", { cache: "no-store" }),
        fetch("/performance/by-symbol", { cache: "no-store" }),
        fetch("/performance/by-timeframe", { cache: "no-store" }),
      ]);
      if (!globalRes.ok || !bySymbolRes.ok || !byTimeframeRes.ok) {
        return;
      }
      const [global, bySymbolData, byTimeframeData] = await Promise.all([
        globalRes.json(),
        bySymbolRes.json(),
        byTimeframeRes.json(),
      ]);
      renderPerformance(global, bySymbolData.by_symbol, byTimeframeData.by_timeframe);
    } catch (_) {
      // silencioso — painel de posições não é afetado
    }
  }

  // ─── Onboarding ────────────────────────────────────────────────────────────

  const STATUS_LABEL = {
    CANDIDATE: "Candidato",
    BACKTESTED: "Backtestado",
    APPROVED: "Aprovado",
  };

  function _obStatusClass(status) {
    if (status === "APPROVED") return "ob-status--approved";
    if (status === "BACKTESTED") return "ob-status--backtested";
    return "ob-status--candidate";
  }

  function _fmtPct(v) {
    return v == null ? "—" : v.toFixed(1) + "%";
  }

  function _fmtNum(v) {
    return v == null ? "—" : v.toFixed(2);
  }

  function renderOnboardingTable(sessions) {
    const tbody = document.getElementById("onboarding-body");
    if (!sessions || sessions.length === 0) {
      tbody.innerHTML = '<tr class="empty-row"><td colspan="10">Nenhuma sessão de onboarding.</td></tr>';
      return;
    }
    tbody.innerHTML = sessions.map((s) => {
      const r = s.backtest_result;
      const trades = r ? r.total_trades : null;
      const wr = r ? r.win_rate_pct : null;
      const pf = r ? r.profit_factor : null;
      const dd = r ? r.max_drawdown_usdt : null;
      const createdAt = s.created_at ? s.created_at.replace("T", " ").slice(0, 16) : "—";
      const statusLabel = STATUS_LABEL[s.status] || s.status;
      const statusClass = _obStatusClass(s.status);

      let actions = "";
      if (s.status === "CANDIDATE" || s.status === "BACKTESTED") {
        actions += `<button class="btn btn-sm btn-backtest" data-symbol="${s.symbol}" data-tf="${s.timeframe}">Backtest</button> `;
      }
      if (s.status === "BACKTESTED") {
        actions += `<button class="btn btn-sm btn-approve" data-symbol="${s.symbol}">Aprovar</button> `;
      }
      if (s.status === "APPROVED") {
        actions += `<button class="btn btn-sm btn-show-config" data-symbol="${s.symbol}" data-config="${s.config_string}">Ver Config</button> `;
      }
      actions += `<button class="btn btn-sm btn-delete-ob" data-symbol="${s.symbol}">Remover</button>`;

      return `<tr>
        <td>${s.symbol}</td>
        <td>${s.timeframe}</td>
        <td>${s.leverage}x</td>
        <td><span class="ob-status ${statusClass}">${statusLabel}</span></td>
        <td>${trades != null ? trades : "—"}</td>
        <td>${_fmtPct(wr)}</td>
        <td>${_fmtNum(pf)}</td>
        <td>${dd != null ? dd.toFixed(2) : "—"}</td>
        <td>${createdAt}</td>
        <td class="ob-actions">${actions}</td>
      </tr>`;
    }).join("");

    tbody.querySelectorAll(".btn-backtest").forEach((btn) => {
      btn.addEventListener("click", () => startOnboardingBacktest(btn.dataset.symbol));
    });
    tbody.querySelectorAll(".btn-approve").forEach((btn) => {
      btn.addEventListener("click", () => approveOnboarding(btn.dataset.symbol));
    });
    tbody.querySelectorAll(".btn-show-config").forEach((btn) => {
      btn.addEventListener("click", () => showOnboardingConfig(btn.dataset.config));
    });
    tbody.querySelectorAll(".btn-delete-ob").forEach((btn) => {
      btn.addEventListener("click", () => deleteOnboardingSession(btn.dataset.symbol));
    });
  }

  async function fetchOnboardingSessions() {
    try {
      const res = await fetch("/onboarding");
      if (!res.ok) return;
      const sessions = await res.json();
      renderOnboardingTable(sessions);
    } catch (_) {}
  }

  async function startOnboardingBacktest(symbol) {
    const btn = document.querySelector(`.btn-backtest[data-symbol="${symbol}"]`);
    if (btn) { btn.disabled = true; btn.textContent = "Rodando…"; }
    try {
      const res = await fetch(`/onboarding/${symbol}/backtest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ limit: 35000 }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(`Backtest falhou: ${err.tipo || err.error || res.status}`);
      }
    } catch (e) {
      alert("Erro de rede ao iniciar backtest.");
    } finally {
      await fetchOnboardingSessions();
    }
  }

  async function approveOnboarding(symbol) {
    if (!confirm(`Aprovar ${symbol} para produção?`)) return;
    try {
      const res = await fetch(`/onboarding/${symbol}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        alert(`Erro ao aprovar: ${err.error || res.status}`);
        return;
      }
      const session = await res.json();
      showOnboardingConfig(session.config_string);
    } catch (_) {
      alert("Erro de rede ao aprovar.");
    } finally {
      await fetchOnboardingSessions();
    }
  }

  function showOnboardingConfig(configString) {
    const box = document.getElementById("onboarding-config-box");
    const pre = document.getElementById("onboarding-config-string");
    if (!configString) return;
    pre.textContent = `SYMBOL_TIMEFRAMES=${configString}`;
    box.hidden = false;
    box.scrollIntoView({ behavior: "smooth" });
  }

  async function deleteOnboardingSession(symbol) {
    if (!confirm(`Remover sessão de onboarding para ${symbol}?`)) return;
    try {
      await fetch(`/onboarding/${symbol}`, { method: "DELETE" });
    } catch (_) {}
    await fetchOnboardingSessions();
  }

  function bindOnboardingForm() {
    const form = document.getElementById("onboarding-form");
    const errEl = document.getElementById("onboarding-form-error");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      errEl.hidden = true;
      const symbol = document.getElementById("ob-symbol").value.trim().toUpperCase();
      const timeframe = document.getElementById("ob-timeframe").value;
      const leverage = parseInt(document.getElementById("ob-leverage").value, 10);

      try {
        const res = await fetch("/onboarding", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ symbol, timeframe, leverage }),
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          errEl.textContent = data.error === "simbolo_ja_ativo"
            ? `${symbol} já está ativo no bot.`
            : data.error === "sessao_ja_existe"
            ? `Sessão para ${symbol} já existe.`
            : data.detalhe || data.error || `Erro ${res.status}`;
          errEl.hidden = false;
          return;
        }
        form.reset();
        document.getElementById("onboarding-form-toggle").open = false;
        await fetchOnboardingSessions();
      } catch (_) {
        errEl.textContent = "Erro de rede.";
        errEl.hidden = false;
      }
    });

    document.getElementById("onboarding-copy-btn")?.addEventListener("click", () => {
      const text = document.getElementById("onboarding-config-string").textContent;
      navigator.clipboard.writeText(text).catch(() => {});
    });
  }

  // ─── Bootstrap ─────────────────────────────────────────────────────────────

  function bootstrap() {
    renderPositions([]);
    renderBotStatus({ status: "inactive", last_activity_at: null });
    renderTradeHistory([]);
    bindPositionFilterEvents();
    bindOnboardingForm();
    setStatus("offline");
    setBanner({ visible: false });
    connect();
    fetchPerformance();
    fetchBotActivity();
    fetchTradeHistory();
    fetchOnboardingSessions();
    window.setInterval(fetchPerformance, PERFORMANCE_POLL_INTERVAL_MS);
    window.setInterval(fetchBotActivity, BOT_ACTIVITY_POLL_INTERVAL_MS);
    window.setInterval(fetchTradeHistory, TRADE_HISTORY_POLL_INTERVAL_MS);
    window.setInterval(fetchOnboardingSessions, 30_000);
  }

  document.addEventListener("DOMContentLoaded", bootstrap);
})();
