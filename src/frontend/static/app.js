(() => {
  const FALLBACK_POLL_INTERVAL_MS = 30_000;
  const MAX_RECONNECT_DELAY_MS = 5_000;
  const PERFORMANCE_POLL_INTERVAL_MS = 60_000;
  const BOT_ACTIVITY_POLL_INTERVAL_MS = 30_000;
  const TRADE_HISTORY_POLL_INTERVAL_MS = 60_000;
  const OPEN_TRADES_POLL_INTERVAL_MS = 60_000;
  const SIGNAL_HISTORY_POLL_INTERVAL_MS = 60_000;

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
    onboardingSessionsMap: {},
    managedSymbol: null,
  };

  const elements = {
    connectionStatus: document.getElementById("connection-status"),
    lastUpdate: document.getElementById("last-update"),
    analysisBiasDirection: document.getElementById("analysis-bias-direction"),
    analysisBiasConfidence: document.getElementById("analysis-bias-confidence"),
    analysisBiasReason: document.getElementById("analysis-bias-reason"),
    analysisOpportunities: document.getElementById("analysis-opportunities"),
    signalDiagnosticBody: document.getElementById("signal-diagnostic-body"),
    banner: document.getElementById("banner"),
    bannerTitle: document.getElementById("banner-title"),
    bannerMessage: document.getElementById("banner-message"),
    summaryExposure: document.getElementById("summary-exposure"),
    summaryMargin: document.getElementById("summary-margin"),
    summaryPnl: document.getElementById("summary-pnl"),
    summaryEquity: document.getElementById("summary-equity"),
    summaryExposureRatio: document.getElementById("summary-exposure-ratio"),
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
    openTradesBody: document.getElementById("open-trades-body"),
    tradeHistoryBody: document.getElementById("trade-history-body"),
    signalHistoryBody: document.getElementById("signal-history-body"),
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

  function getDateTimeLabel(payload, key) {
    if (!payload || typeof payload !== "object") {
      return "—";
    }
    const brKey = `${key}_br`;
    const brValue = String(payload[brKey] || "").trim();
    if (brValue) {
      return brValue;
    }
    return formatDateTimeToLocal(payload[key]);
  }

  function getClockTimeLabel(payload, key) {
    if (!payload || typeof payload !== "object") {
      return "—";
    }
    const brValue = String(payload[`${key}_br`] || "").trim();
    if (brValue) {
      const pieces = brValue.split(" ");
      if (pieces.length >= 2) {
        return pieces[1];
      }
      return brValue;
    }
    return formatClockTime(payload[key]);
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

  function formatRatio(value) {
    if (value === null || value === undefined || value === "—") {
      return "—";
    }
    return `${numberFormatter.format(Number(value))}x`;
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

  function formatTradeStatus(status) {
    const raw = String(status || "").toUpperCase();
    if (raw === "CLOSED_MANUAL") {
      return "CLOSED_EXTERNAL";
    }
    return raw || "—";
  }

  function formatTradeOrigin(trade) {
    const closeReason = String(trade?.close_reason || "");
    const estimated = trade?.is_estimated === true;
    if (!closeReason && !estimated) {
      return "—";
    }

    let label = closeReason || "unknown";
    if (closeReason === "manual_close") {
      label = "Reconciliação externa";
    }

    if (estimated) {
      label += " (estimado)";
    }
    return label;
  }

  function buildTradeStatusTooltip(trade) {
    const status = String(trade?.status || "").toUpperCase();
    const closeReason = String(trade?.close_reason || "");
    const estimated = trade?.is_estimated === true;

    if (status === "CLOSED_MANUAL") {
      return estimated
        ? "Fechado fora do fluxo TP/SL detectado; preço de saída estimado por ticker."
        : "Fechado fora do fluxo TP/SL detectado pelo monitor.";
    }
    if (closeReason) {
      return `close_reason=${closeReason}`;
    }
    return status || "status indisponível";
  }

  function formatSignalExecutionStatus(status) {
    const raw = String(status || "").toUpperCase();
    const labels = {
      TRADE_OPENED: "TRADE_OPENED",
      REJECTED_NO_BALANCE: "REJECTED_NO_BALANCE",
      REJECTED_RISK_MAX_CAPITAL: "REJECTED_RISK_MAX_CAPITAL",
      REJECTED_RISK_ZERO_STOP: "REJECTED_RISK_ZERO_STOP",
      REJECTED_RISK_QTY_ZERO: "REJECTED_RISK_QTY_ZERO",
      REJECTED_RISK_MIN_NOTIONAL: "REJECTED_RISK_MIN_NOTIONAL",
      REJECTED_ORDER_EXECUTION: "REJECTED_ORDER_EXECUTION",
      REJECTED_UNKNOWN: "REJECTED_UNKNOWN",
      UNKNOWN_LEGACY: "UNKNOWN_LEGACY",
    };
    return labels[raw] || raw || "—";
  }

  function buildSignalReason(signal) {
    const reason = String(signal?.execution_reason || "").trim();
    if (reason) {
      return reason;
    }
    if (String(signal?.execution_status || "").toUpperCase() === "UNKNOWN_LEGACY") {
      return "causa indisponível (pré-rastreio)";
    }
    return "—";
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
    elements.summaryEquity.textContent = formatMoney(summary.account_equity_usdt);
    elements.summaryExposureRatio.textContent = formatRatio(summary.exposure_to_equity_ratio);
    elements.lastUpdate.textContent = `Atualizado em ${getDateTimeLabel(summary, "last_update_at")}`;
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

  function renderSignalTelemetry(rows) {
    if (!elements.signalDiagnosticBody) {
      return;
    }
    if (!Array.isArray(rows) || rows.length === 0) {
      elements.signalDiagnosticBody.innerHTML = `
        <tr class="empty-row">
          <td colspan="5">Sem diagnóstico recente.</td>
        </tr>
      `;
      return;
    }

    elements.signalDiagnosticBody.innerHTML = rows
      .map((row) => {
        const decision = String(row?.decision || "UNKNOWN");
        const reason = String(row?.reason || "—");
        const decisionClass =
          row?.signal_generated === true ? "signal-decision-positive" : "signal-decision-neutral";
        return `
          <tr>
            <td>${row?.symbol ?? "—"}</td>
            <td>${row?.timeframe ?? "—"}</td>
            <td class="${decisionClass}">${decision}</td>
            <td>${reason}</td>
            <td>${getDateTimeLabel(row, "evaluated_at")}</td>
          </tr>
        `;
      })
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
            <td>${getDateTimeLabel(position, "updated_at")}</td>
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

    const latestCycle = getClockTimeLabel(data, "last_activity_at");
    elements.botStatusTime.textContent = `Último ciclo: ${latestCycle}`;
    elements.botStatusIndicator.title = `Último ciclo detectado às ${latestCycle}`;
  }

  function renderTradeHistory(trades) {
    if (!Array.isArray(trades) || trades.length === 0) {
      elements.tradeHistoryBody.innerHTML = `
        <tr class="empty-row">
          <td colspan="11">Nenhum trade fechado encontrado.</td>
        </tr>
      `;
      return;
    }

    elements.tradeHistoryBody.innerHTML = trades
      .map((trade) => {
        const pnlClass =
          trade.pnl_usdt == null ? "" : Number(trade.pnl_usdt) >= 0 ? "metric-positive" : "metric-negative";
        const pnlValue = trade.pnl_usdt == null ? "—" : formatMoney(trade.pnl_usdt);
        const statusLabel = formatTradeStatus(trade.status);
        const originLabel = formatTradeOrigin(trade);
        const statusTooltip = buildTradeStatusTooltip(trade);
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
            <td title="${statusTooltip}">${statusLabel}</td>
            <td title="${statusTooltip}">${originLabel}</td>
            <td>${getDateTimeLabel(trade, "closed_at")}</td>
          </tr>
        `;
      })
      .join("");
  }

  function renderOpenTrades(trades) {
    if (!Array.isArray(trades) || trades.length === 0) {
      elements.openTradesBody.innerHTML = `
        <tr class="empty-row">
          <td colspan="6">Nenhum trade aberto encontrado.</td>
        </tr>
      `;
      return;
    }

    elements.openTradesBody.innerHTML = trades
      .map((trade) => {
        const pnlClass =
          trade.unrealized_pnl_usdt == null
            ? ""
            : Number(trade.unrealized_pnl_usdt) >= 0
              ? "metric-positive"
              : "metric-negative";
        const pnlValue =
          trade.unrealized_pnl_usdt == null ? "—" : formatMoney(trade.unrealized_pnl_usdt);

        return `
          <tr>
            <td>${getDateTimeLabel(trade, "opened_at")}</td>
            <td>${trade.symbol ?? "—"}</td>
            <td>${formatMoney(trade.margin_used_usdt)}</td>
            <td>${formatPrice(trade.entry_price)}</td>
            <td>${formatPrice(trade.current_price)}</td>
            <td class="${pnlClass}">${pnlValue}</td>
          </tr>
        `;
      })
      .join("");
  }

  function renderSignalHistory(signals) {
    if (!elements.signalHistoryBody) {
      return;
    }
    if (!Array.isArray(signals) || signals.length === 0) {
      elements.signalHistoryBody.innerHTML = `
        <tr class="empty-row">
          <td colspan="9">Nenhum sinal detectado.</td>
        </tr>
      `;
      return;
    }

    elements.signalHistoryBody.innerHTML = signals
      .map((signal) => {
        const statusLabel = formatSignalExecutionStatus(signal.execution_status);
        const reason = buildSignalReason(signal);
        const statusClass = statusLabel === "TRADE_OPENED" ? "metric-positive" : "metric-negative";
        return `
          <tr>
            <td>${getDateTimeLabel(signal, "detected_at")}</td>
            <td>${signal.symbol ?? "—"}</td>
            <td>${signal.timeframe ?? "—"}</td>
            <td>${String(signal.direction ?? "—").toUpperCase()}</td>
            <td>${formatPrice(signal.entry_price)}</td>
            <td>${formatPrice(signal.stop_loss)}</td>
            <td>${formatPrice(signal.take_profit)}</td>
            <td class="${statusClass}">${statusLabel}</td>
            <td>${reason}</td>
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

  async function fetchOpenTrades() {
    try {
      const response = await fetch("/trades/open", { cache: "no-store" });
      if (!response.ok) {
        return;
      }
      const payload = await response.json();
      renderOpenTrades(payload.trades);
    } catch (_) {
      // silencioso — painel de posições não é afetado
    }
  }

  async function fetchSignalHistory() {
    try {
      const response = await fetch("/signals/history", { cache: "no-store" });
      if (!response.ok) {
        return;
      }
      const payload = await response.json();
      renderSignalHistory(payload.signals);
    } catch (_) {
      // silencioso — painel de posições não é afetado
    }
  }

  function renderSnapshot(snapshot) {
    state.lastSnapshot = snapshot;
    renderPositions(snapshot.positions);
    renderSummary(snapshot.summary);
    renderMarketAnalysis(snapshot.analysis);
    renderSignalTelemetry(snapshot.signal_telemetry);
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

  const ONBOARDING_COLUMNS = 10;

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

  function setManageStatus(message, type = "info") {
    const statusEl = document.getElementById("onboarding-manage-status");
    if (!statusEl) return;
    if (!message) {
      statusEl.hidden = true;
      statusEl.textContent = "";
      statusEl.className = "onboarding-manage-status";
      return;
    }
    statusEl.hidden = false;
    statusEl.textContent = message;
    statusEl.className = `onboarding-manage-status onboarding-manage-status--${type}`;
  }

  function _backtestSummary(payload) {
    const result = payload?.backtest_result || {};
    const totalTrades = result.total_trades ?? "—";
    const winRate = result.win_rate_pct != null ? `${result.win_rate_pct.toFixed(2)}%` : "—";
    const pf = result.profit_factor != null ? result.profit_factor.toFixed(2) : "—";
    return `Backtest concluído: trades=${totalTrades}, win_rate=${winRate}, PF=${pf}.`;
  }

  function _renderOnboardingError(error, symbol) {
    if (error === "simbolo_ja_ativo") return `${symbol} já está ativo no bot.`;
    if (error === "sessao_ja_existe") return `Sessão para ${symbol} já existe.`;
    if (error === "timeframe_invalido") return "Timeframe inválido.";
    if (error === "leverage_invalido") return "Alavancagem inválida.";
    return error || "Erro inesperado.";
  }

  function renderOnboardingTable(sessions) {
    const tbody = document.getElementById("onboarding-body");
    if (!sessions || sessions.length === 0) {
      state.onboardingSessionsMap = {};
      tbody.innerHTML = `<tr class="empty-row"><td colspan="${ONBOARDING_COLUMNS}">Nenhuma sessão de onboarding.</td></tr>`;
      return;
    }
    state.onboardingSessionsMap = Object.fromEntries(
      sessions.map((session) => [session.symbol, session]),
    );

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
        actions += `<button class="btn btn-sm btn-manage" data-symbol="${s.symbol}">Gerenciar</button> `;
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
    tbody.querySelectorAll(".btn-manage").forEach((btn) => {
      btn.addEventListener("click", () => openOnboardingManagePanel(btn.dataset.symbol));
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
    const tableButtons = Array.from(
      document.querySelectorAll(`.btn-backtest[data-symbol="${symbol}"]`),
    );
    const manageButton = document.getElementById("ob-manage-backtest-btn");
    const manageContext = state.managedSymbol === symbol;
    const manageButtonInitialText = manageButton?.textContent || "Backtest";
    tableButtons.forEach((button) => {
      button.disabled = true;
      button.textContent = "Rodando…";
    });
    if (manageContext && manageButton) {
      manageButton.disabled = true;
      manageButton.textContent = "Rodando backtest…";
      setManageStatus("Backtest em execução. Isso pode levar alguns segundos.", "info");
    }

    try {
      const res = await fetch(`/onboarding/${symbol}/backtest`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ limit: 35000 }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        if (manageContext) {
          setManageStatus(
            `Falha no backtest: ${err.tipo || err.error || res.status}.`,
            "error",
          );
        }
        alert(`Backtest falhou: ${err.tipo || err.error || res.status}`);
        return;
      }
      const payload = await res.json().catch(() => ({}));
      if (payload.symbol_timeframes_line || payload.config_string) {
        showOnboardingConfig(payload.symbol_timeframes_line || payload.config_string);
      }
      if (state.managedSymbol === symbol) {
        renderManageResult(payload, "Backtest executado.");
        setManageStatus(_backtestSummary(payload), "success");
      }
    } catch (e) {
      if (manageContext) {
        setManageStatus("Erro de rede ao iniciar backtest.", "error");
      }
      alert("Erro de rede ao iniciar backtest.");
    } finally {
      await fetchOnboardingSessions();
      tableButtons.forEach((button) => {
        button.disabled = false;
        button.textContent = "Backtest";
      });
      if (manageContext && manageButton) {
        manageButton.disabled = false;
        manageButton.textContent = manageButtonInitialText;
      }
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
      showOnboardingConfig(session.symbol_timeframes_line || session.config_string);
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

  function renderManageResult(payload, prefix = "Resposta recebida.") {
    const result = document.getElementById("onboarding-manage-result");
    if (!result) return;
    result.hidden = false;
    result.textContent = `${prefix}\n${JSON.stringify(payload, null, 2)}`;
  }

  function openOnboardingManagePanel(symbol) {
    const session = state.onboardingSessionsMap[symbol];
    if (!session) return;

    const box = document.getElementById("onboarding-manage-box");
    const errEl = document.getElementById("onboarding-manage-error");
    const result = document.getElementById("onboarding-manage-result");
    document.getElementById("ob-manage-current-symbol").value = session.symbol;
    document.getElementById("ob-manage-symbol").value = session.symbol;
    document.getElementById("ob-manage-timeframe").value = session.timeframe;
    document.getElementById("ob-manage-leverage").value = String(session.leverage);
    if (errEl) {
      errEl.hidden = true;
      errEl.textContent = "";
    }
    if (result) {
      result.hidden = true;
      result.textContent = "";
    }
    setManageStatus("");
    state.managedSymbol = session.symbol;
    box.hidden = false;
    box.scrollIntoView({ behavior: "smooth" });
  }

  async function saveManagedSession(event) {
    event.preventDefault();
    const currentSymbol = document.getElementById("ob-manage-current-symbol").value.trim().toUpperCase();
    const nextSymbol = document.getElementById("ob-manage-symbol").value.trim().toUpperCase();
    const timeframe = document.getElementById("ob-manage-timeframe").value;
    const leverage = parseInt(document.getElementById("ob-manage-leverage").value, 10);
    const errEl = document.getElementById("onboarding-manage-error");
    errEl.hidden = true;

    try {
      const res = await fetch(`/onboarding/${currentSymbol}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol: nextSymbol, timeframe, leverage }),
      });
      const payload = await res.json().catch(() => ({}));
      if (!res.ok) {
        errEl.textContent = _renderOnboardingError(payload.error || payload.detalhe, nextSymbol);
        errEl.hidden = false;
        return;
      }
      state.managedSymbol = payload.symbol;
      document.getElementById("ob-manage-current-symbol").value = payload.symbol;
      showOnboardingConfig(payload.symbol_timeframes_line || payload.config_string);
      renderManageResult(payload, "Configuração salva.");
      setManageStatus("Configuração atualizada com sucesso.", "success");
      await fetchOnboardingSessions();
    } catch (_) {
      errEl.textContent = "Erro de rede ao salvar configuração.";
      errEl.hidden = false;
    }
  }

  async function runManagedBacktest() {
    const currentSymbol = document.getElementById("ob-manage-current-symbol").value.trim().toUpperCase();
    if (!currentSymbol) return;
    await startOnboardingBacktest(currentSymbol);
  }

  async function runManagedMarketAnalysis() {
    const currentSymbol = document.getElementById("ob-manage-current-symbol").value.trim().toUpperCase();
    const errEl = document.getElementById("onboarding-manage-error");
    if (!currentSymbol) return;
    errEl.hidden = true;

    try {
      const res = await fetch(`/onboarding/${currentSymbol}/market-analysis`, {
        method: "POST",
      });
      const payload = await res.json().catch(() => ({}));
      if (!res.ok) {
        errEl.textContent = payload.tipo || payload.error || "Falha ao analisar mercado.";
        errEl.hidden = false;
        setManageStatus("Falha na análise técnica.", "error");
        return;
      }
      renderManageResult(payload, "Análise técnica atual concluída.");
      setManageStatus("Análise técnica concluída.", "success");
    } catch (_) {
      errEl.textContent = "Erro de rede ao solicitar análise.";
      errEl.hidden = false;
      setManageStatus("Erro de rede ao solicitar análise.", "error");
    }
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

    document.getElementById("onboarding-manage-form")?.addEventListener("submit", saveManagedSession);
    document.getElementById("ob-manage-backtest-btn")?.addEventListener("click", runManagedBacktest);
    document.getElementById("ob-manage-analysis-btn")?.addEventListener("click", runManagedMarketAnalysis);
  }

  // ─── Bootstrap ─────────────────────────────────────────────────────────────

  function bootstrap() {
    renderPositions([]);
    renderSignalTelemetry([]);
    renderBotStatus({ status: "inactive", last_activity_at: null });
    renderOpenTrades([]);
    renderTradeHistory([]);
    renderSignalHistory([]);
    bindPositionFilterEvents();
    bindOnboardingForm();
    setStatus("offline");
    setBanner({ visible: false });
    connect();
    fetchPerformance();
    fetchBotActivity();
    fetchOpenTrades();
    fetchTradeHistory();
    fetchSignalHistory();
    fetchOnboardingSessions();
    window.setInterval(fetchPerformance, PERFORMANCE_POLL_INTERVAL_MS);
    window.setInterval(fetchBotActivity, BOT_ACTIVITY_POLL_INTERVAL_MS);
    window.setInterval(fetchOpenTrades, OPEN_TRADES_POLL_INTERVAL_MS);
    window.setInterval(fetchTradeHistory, TRADE_HISTORY_POLL_INTERVAL_MS);
    window.setInterval(fetchSignalHistory, SIGNAL_HISTORY_POLL_INTERVAL_MS);
    window.setInterval(fetchOnboardingSessions, 30_000);
  }

  document.addEventListener("DOMContentLoaded", bootstrap);
})();
