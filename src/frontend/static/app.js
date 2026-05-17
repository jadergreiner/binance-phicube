(() => {
  const FALLBACK_POLL_INTERVAL_MS = 30_000;
  const MAX_RECONNECT_DELAY_MS = 5_000;
  const PERFORMANCE_POLL_INTERVAL_MS = 60_000;
  const BOT_ACTIVITY_POLL_INTERVAL_MS = 30_000;
  const TRADE_HISTORY_POLL_INTERVAL_MS = 60_000;
  const OPEN_TRADES_POLL_INTERVAL_MS = 60_000;
  const SIGNAL_HISTORY_POLL_INTERVAL_MS = 60_000;
  const ASSERTIVENESS_POLL_INTERVAL_MS = 60_000;
  const SYMBOLS_OVERVIEW_POLL_INTERVAL_MS = 60_000;

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
    biasViews: [],
    activeBiasView: "allocation",
    sortKey: "symbol",
    sortDir: "asc",
    tradeHistory: [],
    assertiveness: {
      symbol: "",
      timeframe: "",
      period: "30d",
      start: "",
      end: "",
    },
    activeTab: "overview",
    symbolsView: {
      symbol: "",
      timeframe: "15m",
    },
    symbolsOverview: {
      riskStatus: "",
      symbolQuery: "",
      sortKey: "risk_status",
      sortDir: "asc",
    },
  };

  const elements = {
    connectionStatus: document.getElementById("connection-status"),
    lastUpdate: document.getElementById("last-update"),
    analysisBiasDirection: document.getElementById("analysis-bias-direction"),
    analysisBiasConfidence: document.getElementById("analysis-bias-confidence"),
    analysisBiasReason: document.getElementById("analysis-bias-reason"),
    analysisBiasView: document.getElementById("analysis-bias-view"),
    analysisBiasDivergence: document.getElementById("analysis-bias-divergence"),
    analysisBiasMetrics: document.getElementById("analysis-bias-metrics"),
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
    sortKey: document.getElementById("sort-key"),
    sortDir: document.getElementById("sort-dir"),
    saveViewBtn: document.getElementById("save-view-btn"),
    positionsLiveRegion: document.getElementById("positions-live-region"),
    directionButtons: Array.from(document.querySelectorAll(".dir-btn")),
    openTradesBody: document.getElementById("open-trades-body"),
    tradeHistoryBody: document.getElementById("trade-history-body"),
    signalHistoryBody: document.getElementById("signal-history-body"),
    topSymbolsProfitable: document.getElementById("top-symbols-profitable"),
    topSymbolsLosing: document.getElementById("top-symbols-losing"),
    bestTrade: document.getElementById("best-trade"),
    worstTrade: document.getElementById("worst-trade"),
    assertivenessSymbol: document.getElementById("assertiveness-symbol"),
    assertivenessTimeframe: document.getElementById("assertiveness-timeframe"),
    assertivenessPeriod: document.getElementById("assertiveness-period"),
    assertivenessStart: document.getElementById("assertiveness-start"),
    assertivenessEnd: document.getElementById("assertiveness-end"),
    assertivenessLiveRegion: document.getElementById("assertiveness-live-region"),
    assertivenessSummaryAssertiveness: document.getElementById("assertiveness-summary-assertiveness"),
    assertivenessSummarySignals: document.getElementById("assertiveness-summary-signals"),
    assertivenessSummaryTrades: document.getElementById("assertiveness-summary-trades"),
    assertivenessSummaryConversion: document.getElementById("assertiveness-summary-conversion"),
    assertivenessRankingBody: document.getElementById("assertiveness-ranking-body"),
    assertivenessTimelineBody: document.getElementById("assertiveness-timeline-body"),
    symbolsOverviewStatus: document.getElementById("symbols-overview-status"),
    symbolsOverviewCountOk: document.getElementById("symbols-overview-count-ok"),
    symbolsOverviewCountAtencao: document.getElementById("symbols-overview-count-atencao"),
    symbolsOverviewCountBloqueado: document.getElementById("symbols-overview-count-bloqueado"),
    symbolsOverviewBody: document.getElementById("symbols-overview-body"),
    symbolsOverviewFilterRisk: document.getElementById("symbols-overview-filter-risk"),
    symbolsOverviewFilterSymbol: document.getElementById("symbols-overview-filter-symbol"),
    symbolsOverviewSortKey: document.getElementById("symbols-overview-sort-key"),
    symbolsOverviewSortDir: document.getElementById("symbols-overview-sort-dir"),
    symbolsOverviewSortChip: document.getElementById("symbols-overview-sort-chip"),
    symbolsOverviewClearFilters: document.getElementById("symbols-overview-clear-filters"),
    symbolsOverviewLiveRegion: document.getElementById("symbols-overview-live-region"),
    symbolsDetailStatus: document.getElementById("symbols-detail-status"),
    symbolsDetailSymbol: document.getElementById("symbols-detail-symbol"),
    symbolsDetailTimeframe: document.getElementById("symbols-detail-timeframe"),
    symbolsDetailSymbolValue: document.getElementById("symbols-detail-symbol-value"),
    symbolsDetailTimeframeValue: document.getElementById("symbols-detail-timeframe-value"),
    symbolsDetailRiskValue: document.getElementById("symbols-detail-risk-value"),
    symbolsDetailDecisionValue: document.getElementById("symbols-detail-decision-value"),
    symbolsDetailHumanValue: document.getElementById("symbols-detail-human-value"),
    symbolsDetailLevelsValue: document.getElementById("symbols-detail-levels-value"),
    symbolsDetailZonesValue: document.getElementById("symbols-detail-zones-value"),
    tabButtons: Array.from(document.querySelectorAll(".tab-btn")),
    tabSections: Array.from(document.querySelectorAll(".tab-section")),
  };
  const POSITION_VIEW_STORAGE_KEY = "phicube_positions_view_v2";
  const ASSERTIVENESS_VIEW_STORAGE_KEY = "phicube_assertiveness_view_v1";
  const ACTIVE_TAB_STORAGE_KEY = "phicube_active_tab_v1";
  const SYMBOLS_OVERVIEW_VIEW_STORAGE_KEY = "phicube_symbols_overview_view_v1";
  const A11Y_MESSAGES = {
    symbols: {
      riskApplied: (risk) => `Filtro de risco aplicado: ${risk}`,
      riskRemoved: "Filtro de risco removido",
      symbolApplied: (symbol) => `Filtro de símbolo aplicado: ${symbol}`,
      symbolRemoved: "Filtro de símbolo removido",
      sortChanged: (sortKey) => `Ordenação alterada para: ${sortKey}`,
      sortDirChanged: (sortDir) => `Direção de ordenação alterada para: ${sortDir}`,
      reset: "Filtros de símbolos resetados para o padrão",
    },
    positions: {
      symbolApplied: (symbol) => `Filtro de símbolo aplicado: ${symbol}`,
      symbolRemoved: "Filtro de símbolo removido",
      directionApplied: (direction) => `Filtro de direção aplicado: ${direction}`,
      directionRemoved: "Filtro de direção removido",
      sortChanged: (sortKey) => `Ordenação alterada para: ${sortKey}`,
      sortDirChanged: (sortDir) => `Direção de ordenação alterada para: ${sortDir}`,
      viewSaved: "Visão de posições salva",
    },
    assertiveness: {
      symbolApplied: (symbol) => `Assertividade filtrada por símbolo: ${symbol}`,
      symbolRemoved: "Filtro de símbolo da assertividade removido",
      timeframeApplied: (timeframe) => `Assertividade filtrada por timeframe: ${timeframe}`,
      timeframeRemoved: "Filtro de timeframe da assertividade removido",
      periodChanged: (period) => `Período da assertividade alterado para: ${period}`,
      startUpdated: "Data inicial da assertividade atualizada",
      endUpdated: "Data final da assertividade atualizada",
    },
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
    minimumFractionDigits: 2,
    maximumFractionDigits: 8,
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
      if (elements.analysisBiasDivergence) {
        elements.analysisBiasDivergence.textContent = "Sem divergência entre visões.";
      }
      if (elements.analysisBiasMetrics) {
        elements.analysisBiasMetrics.textContent = "—";
      }
      elements.analysisOpportunities.innerHTML = "<li>Nenhuma oportunidade detectada.</li>";
      return;
    }
    renderBiasViews(analysis);
    elements.analysisOpportunities.innerHTML = renderOpportunities(analysis.opportunities);
  }

  function populateBiasViewSelector(views, activeId) {
    if (!elements.analysisBiasView) {
      return;
    }
    const validViews = Array.isArray(views) ? views : [];
    if (validViews.length === 0) {
      elements.analysisBiasView.innerHTML = '<option value="allocation">allocation</option>';
      elements.analysisBiasView.value = "allocation";
      state.activeBiasView = "allocation";
      return;
    }
    elements.analysisBiasView.innerHTML = validViews
      .map((view) => `<option value="${view.id}">${view.id}</option>`)
      .join("");
    state.activeBiasView = activeId || validViews[0].id;
    elements.analysisBiasView.value = state.activeBiasView;
  }

  function renderBiasDetails(selectedView, divergence) {
    if (!selectedView) {
      return;
    }
    elements.analysisBiasDirection.textContent = selectedView.direction;
    elements.analysisBiasConfidence.textContent = selectedView.confidence;
    elements.analysisBiasReason.textContent = selectedView.reason;
    if (elements.analysisBiasDivergence) {
      const divergenceSummary = divergence?.summary || "Sem divergência entre visões.";
      elements.analysisBiasDivergence.textContent = divergenceSummary;
    }
    if (elements.analysisBiasMetrics) {
      elements.analysisBiasMetrics.textContent = JSON.stringify(selectedView.metrics || {}, null, 2);
    }
  }

  function renderBiasViews(analysis) {
    const fallbackBias = analysis?.bias || {
      direction: "NEUTRAL",
      confidence: "low",
      score: 0,
      reason: "Sem dados de bias.",
    };
    const biasViewsPayload = analysis?.bias_views;
    const views = Array.isArray(biasViewsPayload?.views) && biasViewsPayload.views.length > 0
      ? biasViewsPayload.views
      : [{
          id: "allocation",
          direction: fallbackBias.direction,
          confidence: fallbackBias.confidence,
          score: fallbackBias.score,
          reason: fallbackBias.reason,
          metrics: {},
        }];
    const activeId = biasViewsPayload?.active || "allocation";
    state.biasViews = views;
    populateBiasViewSelector(views, activeId);
    const selectedView = views.find((view) => view.id === state.activeBiasView) || views[0];
    renderBiasDetails(selectedView, biasViewsPayload?.divergence);
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

  function populateAssertivenessSymbolFilter(positions) {
    if (!elements.assertivenessSymbol) {
      return;
    }
    const symbols = [...new Set((positions || []).map((position) => position.symbol).filter(Boolean))].sort();
    const options = [
      '<option value="">Todos os símbolos</option>',
      ...symbols.map((symbol) => `<option value="${symbol}">${symbol}</option>`),
    ];
    elements.assertivenessSymbol.innerHTML = options.join("");
    elements.assertivenessSymbol.value = state.assertiveness.symbol;
  }

  function renderPositionsEmptyRow(message) {
    elements.positionsBody.innerHTML = `
      <tr class="empty-row">
        <td colspan="14">${message}</td>
      </tr>
    `;
  }

  function applyPositionSorting(positions) {
    const rows = [...positions];
    rows.sort((left, right) => {
      if (state.sortKey === "symbol") {
        return String(left.symbol || "").localeCompare(String(right.symbol || ""), "pt-BR");
      }
      const leftValue = Number(left[state.sortKey] ?? 0);
      const rightValue = Number(right[state.sortKey] ?? 0);
      return leftValue - rightValue;
    });
    if (state.sortDir === "desc") {
      rows.reverse();
    }
    return rows;
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

    renderPositionRows(applyPositionSorting(filteredPositions));
  }

  function bindPositionFilterEvents() {
    if (elements.filterSymbol) {
      elements.filterSymbol.addEventListener("change", (event) => {
        state.filterSymbol = event.target.value;
      announceLiveRegion(
        elements.positionsLiveRegion,
        state.filterSymbol
          ? A11Y_MESSAGES.positions.symbolApplied(state.filterSymbol)
          : A11Y_MESSAGES.positions.symbolRemoved,
        );
        applyPositionFilters();
      });
    }

    elements.directionButtons.forEach((button) => {
      button.addEventListener("click", () => {
        state.filterDirection = button.dataset.dir || "";
        elements.directionButtons.forEach((innerButton) => {
          innerButton.classList.toggle("active", innerButton === button);
        });
        announceLiveRegion(
          elements.positionsLiveRegion,
          state.filterDirection
            ? A11Y_MESSAGES.positions.directionApplied(state.filterDirection.toUpperCase())
            : A11Y_MESSAGES.positions.directionRemoved,
        );
        applyPositionFilters();
      });
    });

    if (elements.sortKey) {
      elements.sortKey.addEventListener("change", (event) => {
        state.sortKey = event.target.value || "symbol";
        announceLiveRegion(
          elements.positionsLiveRegion,
          A11Y_MESSAGES.positions.sortChanged(state.sortKey),
        );
        applyPositionFilters();
      });
    }

    if (elements.sortDir) {
      elements.sortDir.addEventListener("change", (event) => {
        state.sortDir = event.target.value === "desc" ? "desc" : "asc";
        announceLiveRegion(
          elements.positionsLiveRegion,
          A11Y_MESSAGES.positions.sortDirChanged(state.sortDir),
        );
        applyPositionFilters();
      });
    }

    if (elements.saveViewBtn) {
      elements.saveViewBtn.addEventListener("click", () => {
        persistPositionViewPreference();
        announceLiveRegion(elements.positionsLiveRegion, A11Y_MESSAGES.positions.viewSaved);
      });
    }
  }

  function bindAnalysisViewEvents() {
    if (!elements.analysisBiasView) {
      return;
    }
    elements.analysisBiasView.addEventListener("change", (event) => {
      state.activeBiasView = event.target.value;
      const selectedView = state.biasViews.find((view) => view.id === state.activeBiasView);
      if (!selectedView) {
        return;
      }
      const fallbackDivergence = { summary: "Sem divergência entre visões." };
      const divergence = state.lastSnapshot?.analysis?.bias_views?.divergence || fallbackDivergence;
      renderBiasDetails(selectedView, divergence);
    });
  }

  function renderPositions(positions) {
    state.positions = Array.isArray(positions) ? positions : [];
    populateSymbolFilter(state.positions);
    populateAssertivenessSymbolFilter(state.positions);
    applyPositionFilters();
    renderPositionHighlights(state.positions);
  }

  function persistPositionViewPreference() {
    const payload = {
      filterSymbol: state.filterSymbol,
      filterDirection: state.filterDirection,
      sortKey: state.sortKey,
      sortDir: state.sortDir,
    };
    window.localStorage.setItem(POSITION_VIEW_STORAGE_KEY, JSON.stringify(payload));
  }

  function restorePositionViewPreference() {
    try {
      const raw = window.localStorage.getItem(POSITION_VIEW_STORAGE_KEY);
      if (!raw) {
        return;
      }
      const parsed = JSON.parse(raw);
      state.filterSymbol = String(parsed.filterSymbol || "");
      state.filterDirection = String(parsed.filterDirection || "");
      state.sortKey = String(parsed.sortKey || "symbol");
      state.sortDir = parsed.sortDir === "desc" ? "desc" : "asc";
      if (elements.sortKey) {
        elements.sortKey.value = state.sortKey;
      }
      if (elements.sortDir) {
        elements.sortDir.value = state.sortDir;
      }
      elements.directionButtons.forEach((button) => {
        button.classList.toggle("active", (button.dataset.dir || "") === state.filterDirection);
      });
    } catch (_) {
      // preferência inválida ignorada
    }
  }

  function renderPositionHighlights(positions) {
    if (!Array.isArray(positions) || positions.length === 0) {
      elements.topSymbolsProfitable.textContent = "—";
      elements.topSymbolsLosing.textContent = "—";
      return;
    }

    const sortedByPnl = [...positions].sort(
      (left, right) => Number(right.unrealized_pnl_usdt ?? 0) - Number(left.unrealized_pnl_usdt ?? 0),
    );
    const profitable = sortedByPnl
      .filter((row) => Number(row.unrealized_pnl_usdt ?? 0) > 0)
      .slice(0, 3)
      .map((row) => `${row.symbol} (${formatMoney(row.unrealized_pnl_usdt)})`)
      .join(" | ");
    const losing = [...sortedByPnl]
      .reverse()
      .filter((row) => Number(row.unrealized_pnl_usdt ?? 0) < 0)
      .slice(0, 3)
      .map((row) => `${row.symbol} (${formatMoney(row.unrealized_pnl_usdt)})`)
      .join(" | ");
    elements.topSymbolsProfitable.textContent = profitable || "Sem lucro aberto";
    elements.topSymbolsLosing.textContent = losing || "Sem perdas abertas";
  }

  function restoreAssertivenessViewPreference() {
    try {
      const raw = window.localStorage.getItem(ASSERTIVENESS_VIEW_STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      state.assertiveness.symbol = String(parsed.symbol || "");
      state.assertiveness.timeframe = String(parsed.timeframe || "");
      state.assertiveness.period = String(parsed.period || "30d");
      state.assertiveness.start = String(parsed.start || "");
      state.assertiveness.end = String(parsed.end || "");
    } catch (_) {
      // ignora storage inválido
    }
    if (elements.assertivenessSymbol) elements.assertivenessSymbol.value = state.assertiveness.symbol;
    if (elements.assertivenessTimeframe) {
      elements.assertivenessTimeframe.value = state.assertiveness.timeframe;
    }
    if (elements.assertivenessPeriod) elements.assertivenessPeriod.value = state.assertiveness.period;
    if (elements.assertivenessStart) elements.assertivenessStart.value = state.assertiveness.start;
    if (elements.assertivenessEnd) elements.assertivenessEnd.value = state.assertiveness.end;
    syncAssertivenessCustomControls();
  }

  function persistAssertivenessViewPreference() {
    window.localStorage.setItem(ASSERTIVENESS_VIEW_STORAGE_KEY, JSON.stringify(state.assertiveness));
  }

  function renderAssertiveness(payload) {
    const summary = payload?.summary || {};
    elements.assertivenessSummaryAssertiveness.textContent = formatPercent(summary.assertiveness_pct || 0);
    elements.assertivenessSummarySignals.textContent = formatNumber(summary.total_signals || 0);
    elements.assertivenessSummaryTrades.textContent = formatNumber(summary.total_trades || 0);
    elements.assertivenessSummaryConversion.textContent = formatPercent(
      summary.signal_to_trade_conversion_pct || 0,
    );

    const ranking = Array.isArray(payload?.ranking) ? payload.ranking : [];
    if (ranking.length === 0) {
      elements.assertivenessRankingBody.innerHTML =
        '<tr class="empty-row"><td colspan="8">Sem dados.</td></tr>';
    } else {
      elements.assertivenessRankingBody.innerHTML = ranking
        .map(
          (row) => `
            <tr>
              <td>${row.symbol ?? "—"}</td>
              <td>${formatPercent(row.assertiveness_pct)}</td>
              <td>${formatNumber(row.total_signals)}</td>
              <td>${formatNumber(row.total_trades)}</td>
              <td>${formatPercent(row.signal_to_trade_conversion_pct)}</td>
              <td>${formatMoney(row.pnl_usdt)}</td>
              <td>${formatNumber(row.profit_factor)}</td>
              <td>${formatMoney(row.max_drawdown_usdt)}</td>
            </tr>
          `,
        )
        .join("");
    }

    const timeline = Array.isArray(payload?.timeline) ? payload.timeline : [];
    if (timeline.length === 0) {
      elements.assertivenessTimelineBody.innerHTML =
        '<tr class="empty-row"><td colspan="4">Sem dados.</td></tr>';
      return;
    }
    elements.assertivenessTimelineBody.innerHTML = timeline
      .map(
        (row) => `
          <tr>
            <td>${row.bucket ?? "—"}</td>
            <td>${formatPercent(row.assertiveness_pct)}</td>
            <td>${formatNumber(row.total_trades)}</td>
            <td>${formatMoney(row.pnl_usdt)}</td>
          </tr>
        `,
      )
      .join("");
  }

  async function fetchAssertiveness() {
    try {
      const params = new URLSearchParams({
        period: state.assertiveness.period || "30d",
        order_by: "assertiveness_pct",
        order_dir: "desc",
      });
      if (state.assertiveness.symbol) params.set("symbol", state.assertiveness.symbol);
      if (state.assertiveness.timeframe) params.set("timeframe", state.assertiveness.timeframe);
      if (state.assertiveness.period === "custom") {
        if (!state.assertiveness.start || !state.assertiveness.end) {
          return;
        }
        if (state.assertiveness.start) {
          params.set("start", new Date(state.assertiveness.start).toISOString());
        }
        if (state.assertiveness.end) {
          params.set("end", new Date(state.assertiveness.end).toISOString());
        }
      }
      const response = await fetch(`/performance/assertiveness?${params.toString()}`, {
        cache: "no-store",
      });
      if (!response.ok) return;
      const payload = await response.json();
      renderAssertiveness(payload);
    } catch (_) {
      // silencioso
    }
  }

  function syncAssertivenessCustomControls() {
    const customEnabled = state.assertiveness.period === "custom";
    if (elements.assertivenessStart) {
      elements.assertivenessStart.disabled = !customEnabled;
    }
    if (elements.assertivenessEnd) {
      elements.assertivenessEnd.disabled = !customEnabled;
    }
  }

  function bindAssertivenessEvents() {
    if (elements.assertivenessSymbol) {
      elements.assertivenessSymbol.addEventListener("change", (event) => {
        state.assertiveness.symbol = event.target.value;
        persistAssertivenessViewPreference();
        announceLiveRegion(
          elements.assertivenessLiveRegion,
          state.assertiveness.symbol
            ? A11Y_MESSAGES.assertiveness.symbolApplied(state.assertiveness.symbol)
            : A11Y_MESSAGES.assertiveness.symbolRemoved,
        );
        fetchAssertiveness();
      });
    }
    if (elements.assertivenessTimeframe) {
      elements.assertivenessTimeframe.addEventListener("change", (event) => {
        state.assertiveness.timeframe = event.target.value;
        persistAssertivenessViewPreference();
        announceLiveRegion(
          elements.assertivenessLiveRegion,
          state.assertiveness.timeframe
            ? A11Y_MESSAGES.assertiveness.timeframeApplied(state.assertiveness.timeframe)
            : A11Y_MESSAGES.assertiveness.timeframeRemoved,
        );
        fetchAssertiveness();
      });
    }
    if (elements.assertivenessPeriod) {
      elements.assertivenessPeriod.addEventListener("change", (event) => {
        state.assertiveness.period = event.target.value || "30d";
        syncAssertivenessCustomControls();
        persistAssertivenessViewPreference();
        announceLiveRegion(
          elements.assertivenessLiveRegion,
          A11Y_MESSAGES.assertiveness.periodChanged(state.assertiveness.period),
        );
        fetchAssertiveness();
      });
    }
    if (elements.assertivenessStart) {
      elements.assertivenessStart.addEventListener("change", (event) => {
        state.assertiveness.start = event.target.value || "";
        persistAssertivenessViewPreference();
        announceLiveRegion(
          elements.assertivenessLiveRegion,
          A11Y_MESSAGES.assertiveness.startUpdated,
        );
        if (state.assertiveness.period === "custom") {
          fetchAssertiveness();
        }
      });
    }
    if (elements.assertivenessEnd) {
      elements.assertivenessEnd.addEventListener("change", (event) => {
        state.assertiveness.end = event.target.value || "";
        persistAssertivenessViewPreference();
        announceLiveRegion(
          elements.assertivenessLiveRegion,
          A11Y_MESSAGES.assertiveness.endUpdated,
        );
        if (state.assertiveness.period === "custom") {
          fetchAssertiveness();
        }
      });
    }
  }

  function symbolsOverviewRiskRank(value) {
    const normalized = String(value || "").toLowerCase();
    if (normalized === "bloqueado") return 2;
    if (normalized === "atencao") return 1;
    return 0;
  }

  function persistSymbolsOverviewPreference() {
    try {
      window.localStorage.setItem(
        SYMBOLS_OVERVIEW_VIEW_STORAGE_KEY,
        JSON.stringify(state.symbolsOverview),
      );
    } catch (_) {
      // ignora storage indisponível
    }
  }

  function restoreSymbolsOverviewPreference() {
    try {
      const raw = window.localStorage.getItem(SYMBOLS_OVERVIEW_VIEW_STORAGE_KEY);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      state.symbolsOverview.riskStatus = String(parsed.riskStatus || "");
      state.symbolsOverview.symbolQuery = String(parsed.symbolQuery || "");
      state.symbolsOverview.sortKey = String(parsed.sortKey || "risk_status");
      state.symbolsOverview.sortDir = String(parsed.sortDir || "asc");
    } catch (_) {
      // ignora payload inválido
    }
    if (elements.symbolsOverviewFilterRisk) {
      elements.symbolsOverviewFilterRisk.value = state.symbolsOverview.riskStatus;
    }
    if (elements.symbolsOverviewFilterSymbol) {
      elements.symbolsOverviewFilterSymbol.value = state.symbolsOverview.symbolQuery;
    }
    if (elements.symbolsOverviewSortKey) {
      elements.symbolsOverviewSortKey.value = state.symbolsOverview.sortKey;
    }
    if (elements.symbolsOverviewSortDir) {
      elements.symbolsOverviewSortDir.value = state.symbolsOverview.sortDir;
    }
  }

  function applySymbolsOverviewFiltersAndSort(rows) {
    const filtered = (rows || []).filter((row) => {
      const riskFilter = state.symbolsOverview.riskStatus;
      const query = state.symbolsOverview.symbolQuery.trim().toUpperCase();
      if (riskFilter && String(row.risk_status || "").toLowerCase() !== riskFilter) {
        return false;
      }
      if (query && !String(row.symbol || "").toUpperCase().includes(query)) {
        return false;
      }
      return true;
    });

    const key = state.symbolsOverview.sortKey || "risk_status";
    const dir = state.symbolsOverview.sortDir === "desc" ? -1 : 1;
    filtered.sort((left, right) => {
      if (key === "risk_status") {
        return dir * (symbolsOverviewRiskRank(left.risk_status) - symbolsOverviewRiskRank(right.risk_status));
      }
      if (key === "as_of") {
        const l = new Date(left.as_of || 0).getTime();
        const r = new Date(right.as_of || 0).getTime();
        return dir * (l - r);
      }
      return dir * String(left.symbol || "").localeCompare(String(right.symbol || ""));
    });
    return filtered;
  }

  function renderSymbolsOverviewSortChip() {
    if (!elements.symbolsOverviewSortChip) {
      return;
    }
    const keyMap = {
      risk_status: "risco",
      symbol: "símbolo",
      as_of: "recência",
    };
    const keyLabel = keyMap[state.symbolsOverview.sortKey] || "risco";
    const dirLabel = state.symbolsOverview.sortDir === "desc" ? "desc" : "asc";
    elements.symbolsOverviewSortChip.textContent = `Ordenado por: ${keyLabel} (${dirLabel})`;
  }

  function renderSymbolsOverviewRiskBadgeState() {
    const selected = String(state.symbolsOverview.riskStatus || "");
    const pairs = [
      [elements.symbolsOverviewCountOk, "ok"],
      [elements.symbolsOverviewCountAtencao, "atencao"],
      [elements.symbolsOverviewCountBloqueado, "bloqueado"],
    ];
    pairs.forEach(([el, key]) => {
      if (!el) return;
      const isActive = selected === key;
      el.classList.toggle("risk-badge-active", isActive);
      el.setAttribute("aria-pressed", isActive ? "true" : "false");
    });
  }

  function announceLiveRegion(liveRegionElement, message) {
    if (!liveRegionElement) {
      return;
    }
    liveRegionElement.textContent = "";
    window.setTimeout(() => {
      if (liveRegionElement) {
        liveRegionElement.textContent = String(message || "");
      }
    }, 10);
  }

  function renderSymbolsOverview(payload) {
    const rows = Array.isArray(payload?.symbols) ? payload.symbols : [];
    const sortedRows = applySymbolsOverviewFiltersAndSort(rows);
    renderSymbolsOverviewSortChip();
    renderSymbolsOverviewRiskBadgeState();
    const counts = sortedRows.reduce(
      (acc, row) => {
        const key = String(row.risk_status || "").toLowerCase();
        if (key === "ok") acc.ok += 1;
        else if (key === "atencao") acc.atencao += 1;
        else if (key === "bloqueado") acc.bloqueado += 1;
        return acc;
      },
      { ok: 0, atencao: 0, bloqueado: 0 },
    );
    if (elements.symbolsOverviewCountOk) {
      elements.symbolsOverviewCountOk.textContent = `ok: ${counts.ok}`;
    }
    if (elements.symbolsOverviewCountAtencao) {
      elements.symbolsOverviewCountAtencao.textContent = `atenção: ${counts.atencao}`;
    }
    if (elements.symbolsOverviewCountBloqueado) {
      elements.symbolsOverviewCountBloqueado.textContent = `bloqueado: ${counts.bloqueado}`;
    }
    if (elements.symbolsOverviewStatus) {
      elements.symbolsOverviewStatus.textContent = rows.length ? "online" : "sem dados";
    }
    if (!elements.symbolsOverviewBody) {
      return;
    }
    if (!sortedRows.length) {
      elements.symbolsOverviewBody.innerHTML = `
        <tr class="empty-row">
          <td colspan="5">Sem dados para o filtro aplicado.</td>
        </tr>
      `;
      return;
    }
    elements.symbolsOverviewBody.innerHTML = sortedRows
      .map((row) => {
        const risk = String(row.risk_status || "—");
        return `
          <tr>
            <td>${row.symbol ?? "—"}</td>
            <td>${row.timeframe ?? "—"}</td>
            <td>${row.last_analysis_summary ?? "—"}</td>
            <td>${risk}</td>
            <td>${getDateTimeLabel(row, "as_of")}</td>
          </tr>
        `;
      })
      .join("");
  }

  function renderSymbolDetail(payload) {
    const lastAnalysis = payload?.last_analysis || {};
    const human = lastAnalysis?.human_explanation?.full_text || "—";
    const levels = payload?.chart?.levels || {};
    const zones = Array.isArray(payload?.chart?.watch_zones) ? payload.chart.watch_zones : [];
    const zonesLabel = zones.map((zone) => `${zone.type}:${formatPrice(zone.price_min)}`).join(" | ") || "—";

    elements.symbolsDetailSymbolValue.textContent = payload?.symbol || "—";
    elements.symbolsDetailTimeframeValue.textContent = payload?.timeframe || "—";
    elements.symbolsDetailRiskValue.textContent = payload?.risk?.risk_status || "—";
    elements.symbolsDetailDecisionValue.textContent = lastAnalysis?.classification || "—";
    elements.symbolsDetailHumanValue.textContent = human;
    elements.symbolsDetailLevelsValue.textContent =
      `${formatPrice(levels.entry)} / ${formatPrice(levels.sl)} / ${formatPrice(levels.tp)}`;
    elements.symbolsDetailZonesValue.textContent = zonesLabel;
    if (elements.symbolsDetailStatus) {
      elements.symbolsDetailStatus.textContent = "online";
    }
  }

  function populateSymbolsFilter(rows) {
    if (!elements.symbolsDetailSymbol) {
      return;
    }
    const symbols = [...new Set((rows || []).map((row) => row.symbol).filter(Boolean))].sort();
    const options = [
      `<option value="">Selecione um símbolo</option>`,
      ...symbols.map((symbol) => `<option value="${symbol}">${symbol}</option>`),
    ];
    elements.symbolsDetailSymbol.innerHTML = options.join("");
    if (!state.symbolsView.symbol && symbols.length > 0) {
      state.symbolsView.symbol = symbols[0];
    }
    elements.symbolsDetailSymbol.value = state.symbolsView.symbol;
  }

  async function fetchSymbolsOverview() {
    try {
      const response = await fetch("/symbols/overview", { cache: "no-store" });
      if (!response.ok) {
        if (elements.symbolsOverviewStatus) elements.symbolsOverviewStatus.textContent = "erro";
        return;
      }
      const payload = await response.json();
      renderSymbolsOverview(payload);
      populateSymbolsFilter(payload.symbols || []);
      if (state.symbolsView.symbol) {
        fetchSymbolDetail();
      }
    } catch (_) {
      if (elements.symbolsOverviewStatus) elements.symbolsOverviewStatus.textContent = "erro";
    }
  }

  async function fetchSymbolDetail() {
    const symbol = state.symbolsView.symbol;
    if (!symbol) {
      return;
    }
    const timeframe = state.symbolsView.timeframe || "15m";
    try {
      const response = await fetch(
        `/symbols/${encodeURIComponent(symbol)}/detail?timeframe=${encodeURIComponent(timeframe)}`,
        { cache: "no-store" },
      );
      if (!response.ok) {
        if (elements.symbolsDetailStatus) elements.symbolsDetailStatus.textContent = "erro";
        return;
      }
      const payload = await response.json();
      renderSymbolDetail(payload);
    } catch (_) {
      if (elements.symbolsDetailStatus) elements.symbolsDetailStatus.textContent = "erro";
    }
  }

  function bindSymbolsEvents() {
    function toggleRiskFilter(targetRisk) {
      const normalized = String(targetRisk || "");
      state.symbolsOverview.riskStatus =
        state.symbolsOverview.riskStatus === normalized ? "" : normalized;
      if (elements.symbolsOverviewFilterRisk) {
        elements.symbolsOverviewFilterRisk.value = state.symbolsOverview.riskStatus;
      }
      persistSymbolsOverviewPreference();
      renderSymbolsOverviewRiskBadgeState();
      announceLiveRegion(
        elements.symbolsOverviewLiveRegion,
        state.symbolsOverview.riskStatus
          ? A11Y_MESSAGES.symbols.riskApplied(state.symbolsOverview.riskStatus)
          : A11Y_MESSAGES.symbols.riskRemoved,
      );
      fetchSymbolsOverview();
    }

    if (elements.symbolsOverviewFilterRisk) {
      elements.symbolsOverviewFilterRisk.addEventListener("change", (event) => {
        state.symbolsOverview.riskStatus = String(event.target.value || "");
        persistSymbolsOverviewPreference();
        renderSymbolsOverviewRiskBadgeState();
        announceLiveRegion(
          elements.symbolsOverviewLiveRegion,
          state.symbolsOverview.riskStatus
            ? A11Y_MESSAGES.symbols.riskApplied(state.symbolsOverview.riskStatus)
            : A11Y_MESSAGES.symbols.riskRemoved,
        );
        fetchSymbolsOverview();
      });
    }
    if (elements.symbolsOverviewFilterSymbol) {
      elements.symbolsOverviewFilterSymbol.addEventListener("input", (event) => {
        state.symbolsOverview.symbolQuery = String(event.target.value || "");
        persistSymbolsOverviewPreference();
        announceLiveRegion(
          elements.symbolsOverviewLiveRegion,
          state.symbolsOverview.symbolQuery
            ? A11Y_MESSAGES.symbols.symbolApplied(state.symbolsOverview.symbolQuery)
            : A11Y_MESSAGES.symbols.symbolRemoved,
        );
        fetchSymbolsOverview();
      });
    }
    if (elements.symbolsOverviewSortKey) {
      elements.symbolsOverviewSortKey.addEventListener("change", (event) => {
        state.symbolsOverview.sortKey = String(event.target.value || "risk_status");
        persistSymbolsOverviewPreference();
        announceLiveRegion(
          elements.symbolsOverviewLiveRegion,
          A11Y_MESSAGES.symbols.sortChanged(state.symbolsOverview.sortKey),
        );
        fetchSymbolsOverview();
      });
    }
    if (elements.symbolsOverviewSortDir) {
      elements.symbolsOverviewSortDir.addEventListener("change", (event) => {
        state.symbolsOverview.sortDir = String(event.target.value || "asc");
        persistSymbolsOverviewPreference();
        announceLiveRegion(
          elements.symbolsOverviewLiveRegion,
          A11Y_MESSAGES.symbols.sortDirChanged(state.symbolsOverview.sortDir),
        );
        fetchSymbolsOverview();
      });
    }
    if (elements.symbolsOverviewClearFilters) {
      elements.symbolsOverviewClearFilters.addEventListener("click", () => {
        state.symbolsOverview.riskStatus = "";
        state.symbolsOverview.symbolQuery = "";
        state.symbolsOverview.sortKey = "risk_status";
        state.symbolsOverview.sortDir = "asc";
        if (elements.symbolsOverviewFilterRisk) elements.symbolsOverviewFilterRisk.value = "";
        if (elements.symbolsOverviewFilterSymbol) elements.symbolsOverviewFilterSymbol.value = "";
        if (elements.symbolsOverviewSortKey) elements.symbolsOverviewSortKey.value = "risk_status";
        if (elements.symbolsOverviewSortDir) elements.symbolsOverviewSortDir.value = "asc";
        persistSymbolsOverviewPreference();
        renderSymbolsOverviewSortChip();
        renderSymbolsOverviewRiskBadgeState();
        announceLiveRegion(
          elements.symbolsOverviewLiveRegion,
          A11Y_MESSAGES.symbols.reset,
        );
        fetchSymbolsOverview();
      });
    }
    if (elements.symbolsOverviewCountOk) {
      elements.symbolsOverviewCountOk.addEventListener("click", () => toggleRiskFilter("ok"));
    }
    if (elements.symbolsOverviewCountAtencao) {
      elements.symbolsOverviewCountAtencao.addEventListener("click", () =>
        toggleRiskFilter("atencao"),
      );
    }
    if (elements.symbolsOverviewCountBloqueado) {
      elements.symbolsOverviewCountBloqueado.addEventListener("click", () =>
        toggleRiskFilter("bloqueado"),
      );
    }
    if (elements.symbolsDetailSymbol) {
      elements.symbolsDetailSymbol.addEventListener("change", (event) => {
        state.symbolsView.symbol = event.target.value || "";
        fetchSymbolDetail();
      });
    }
    if (elements.symbolsDetailTimeframe) {
      elements.symbolsDetailTimeframe.addEventListener("change", (event) => {
        state.symbolsView.timeframe = event.target.value || "15m";
        fetchSymbolDetail();
      });
    }
  }

  function applyActiveTab() {
    elements.tabButtons.forEach((button) => {
      button.classList.toggle("active", button.dataset.tab === state.activeTab);
    });
    elements.tabSections.forEach((section) => {
      const targetTab = section.dataset.tab || "overview";
      section.classList.toggle("tab-section-hidden", targetTab !== state.activeTab);
    });
  }

  function bindTabEvents() {
    try {
      const storedTab = window.localStorage.getItem(ACTIVE_TAB_STORAGE_KEY);
      if (storedTab) {
        state.activeTab = storedTab;
      }
    } catch (_) {
      // ignora storage indisponível
    }
    applyActiveTab();
    elements.tabButtons.forEach((button) => {
      button.addEventListener("click", () => {
        state.activeTab = button.dataset.tab || "overview";
        applyActiveTab();
        try {
          window.localStorage.setItem(ACTIVE_TAB_STORAGE_KEY, state.activeTab);
        } catch (_) {
          // ignora storage indisponível
        }
      });
    });
  }

  function renderTradeHighlights(trades) {
    if (!Array.isArray(trades) || trades.length === 0) {
      elements.bestTrade.textContent = "—";
      elements.worstTrade.textContent = "—";
      return;
    }
    const withPnl = trades.filter((trade) => trade.pnl_usdt != null);
    if (withPnl.length === 0) {
      elements.bestTrade.textContent = "Sem PnL";
      elements.worstTrade.textContent = "Sem PnL";
      return;
    }
    const sorted = [...withPnl].sort((left, right) => Number(left.pnl_usdt) - Number(right.pnl_usdt));
    const worst = sorted[0];
    const best = sorted[sorted.length - 1];
    elements.bestTrade.textContent = `${best.symbol ?? "—"} (${formatMoney(best.pnl_usdt)})`;
    elements.worstTrade.textContent = `${worst.symbol ?? "—"} (${formatMoney(worst.pnl_usdt)})`;
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
      state.tradeHistory = Array.isArray(payload.trades) ? payload.trades : [];
      renderTradeHistory(state.tradeHistory);
      renderTradeHighlights(state.tradeHistory);
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
  const BACKTEST_JOB_POLL_INTERVAL_MS = 1_500;
  const BACKTEST_JOB_MAX_POLLS = 240;

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

  function renderOnboardingSyncStatus(syncStatus) {
    const el = document.getElementById("onboarding-sync-status");
    if (!el) return;
    if (!syncStatus || typeof syncStatus !== "object") {
      el.hidden = true;
      el.textContent = "";
      return;
    }
    const consistency = String(syncStatus.consistency_status || "DEGRADED").toUpperCase();
    const isConsistent = consistency === "CONSISTENT";
    if (isConsistent) {
      el.textContent = "Consistência: CONSISTENT (Dashboard/Mongo/.env alinhados).";
      el.style.color = "#86efac";
    } else {
      const error = syncStatus.env_apply_error || "erro não identificado";
      el.textContent = `Consistência: DEGRADED (falha ao aplicar .env: ${error}).`;
      el.style.color = "#fca5a5";
    }
    el.hidden = false;
  }

  function _backtestSummary(payload) {
    const result = payload?.backtest_result || {};
    const totalTrades = result.total_trades ?? "—";
    const winRate = result.win_rate_pct != null ? `${result.win_rate_pct.toFixed(2)}%` : "—";
    const pf = result.profit_factor != null ? result.profit_factor.toFixed(2) : "—";
    return `Backtest concluído: trades=${totalTrades}, win_rate=${winRate}, PF=${pf}.`;
  }

  function _backtestJobStatusLabel(status) {
    const s = String(status || "").toLowerCase();
    if (s === "queued") return "na fila";
    if (s === "running") return "em execução";
    if (s === "succeeded") return "concluído";
    if (s === "failed") return "falhou";
    if (s === "canceled") return "cancelado";
    return status || "desconhecido";
  }

  async function _pollBacktestJob(jobId) {
    for (let attempt = 0; attempt < BACKTEST_JOB_MAX_POLLS; attempt += 1) {
      const res = await fetch(`/onboarding/backtest-jobs/${jobId}`, { cache: "no-store" });
      if (!res.ok) {
        throw new Error(`job_status_http_${res.status}`);
      }
      const payload = await res.json().catch(() => ({}));
      const status = String(payload?.status || "").toLowerCase();
      if (status === "queued" || status === "running") {
        await new Promise((resolve) => window.setTimeout(resolve, BACKTEST_JOB_POLL_INTERVAL_MS));
        continue;
      }
      return payload;
    }
    throw new Error("job_status_timeout");
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
      setManageStatus("Backtest assíncrono iniciado. Aguardando processamento...", "info");
    }

    try {
      const res = await fetch(`/onboarding/${symbol}/backtest-jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ limit: 35000 }),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        if (manageContext) {
          setManageStatus(
            `Falha no backtest: ${err.error_message || err.error_code || res.status}.`,
            "error",
          );
        }
        alert(`Backtest falhou: ${err.error_message || err.error_code || res.status}`);
        return;
      }
      const created = await res.json().catch(() => ({}));
      const jobId = created?.job_id;
      if (!jobId) {
        throw new Error("job_id_missing");
      }
      if (manageContext) {
        setManageStatus(`Backtest ${_backtestJobStatusLabel(created.status)}. Job: ${jobId}`, "info");
      }
      const payload = await _pollBacktestJob(jobId);
      const status = String(payload?.status || "").toLowerCase();
      if (status === "succeeded") {
        if (state.managedSymbol === symbol) {
          renderManageResult(payload, "Backtest assíncrono concluído.");
          setManageStatus(_backtestSummary(payload), "success");
        }
      } else if (manageContext) {
        setManageStatus(
          `Backtest ${_backtestJobStatusLabel(status)}: ${payload?.error_message || payload?.error_code || "sem detalhe"}.`,
          "error",
        );
      }
    } catch (e) {
      if (manageContext) {
        setManageStatus("Erro ao acompanhar job de backtest.", "error");
      }
      alert("Erro ao iniciar/acompanhar backtest.");
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
      renderOnboardingSyncStatus(session.sync_status);
    } catch (_) {
      alert("Erro de rede ao aprovar.");
    } finally {
      await fetchOnboardingSessions();
    }
  }

  function showOnboardingConfig(configString, syncStatus = null) {
    const box = document.getElementById("onboarding-config-box");
    const pre = document.getElementById("onboarding-config-string");
    if (!configString) return;
    pre.textContent = `SYMBOL_TIMEFRAMES=${configString}`;
    renderOnboardingSyncStatus(syncStatus);
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
      showOnboardingConfig(payload.symbol_timeframes_line || payload.config_string, payload.sync_status);
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
      const res = await fetch(`/onboarding/${symbol}`, { method: "DELETE" });
      if (res.ok && res.status !== 204) {
        const payload = await res.json().catch(() => ({}));
        showOnboardingConfig(payload.symbol_timeframes_line, payload.sync_status);
      }
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
    renderTradeHighlights([]);
    renderSignalHistory([]);
    renderAssertiveness({});
    restorePositionViewPreference();
    restoreAssertivenessViewPreference();
    restoreSymbolsOverviewPreference();
    renderSymbolsOverviewSortChip();
    renderSymbolsOverviewRiskBadgeState();
    bindTabEvents();
  bindPositionFilterEvents();
    bindAnalysisViewEvents();
    bindAssertivenessEvents();
    bindSymbolsEvents();
    bindOnboardingForm();
    setStatus("offline");
    setBanner({ visible: false });
    connect();
    fetchPerformance();
    fetchBotActivity();
    fetchOpenTrades();
    fetchTradeHistory();
    fetchSignalHistory();
    fetchAssertiveness();
    fetchSymbolsOverview();
    fetchOnboardingSessions();
    window.setInterval(fetchPerformance, PERFORMANCE_POLL_INTERVAL_MS);
    window.setInterval(fetchBotActivity, BOT_ACTIVITY_POLL_INTERVAL_MS);
    window.setInterval(fetchOpenTrades, OPEN_TRADES_POLL_INTERVAL_MS);
    window.setInterval(fetchTradeHistory, TRADE_HISTORY_POLL_INTERVAL_MS);
    window.setInterval(fetchSignalHistory, SIGNAL_HISTORY_POLL_INTERVAL_MS);
    window.setInterval(fetchAssertiveness, ASSERTIVENESS_POLL_INTERVAL_MS);
    window.setInterval(fetchSymbolsOverview, SYMBOLS_OVERVIEW_POLL_INTERVAL_MS);
    window.setInterval(fetchOnboardingSessions, 30_000);
  }

  document.addEventListener("DOMContentLoaded", bootstrap);
})();
