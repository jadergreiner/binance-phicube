(() => {
  const state = {
    socket: null,
    reconnectTimer: null,
    reconnectAttempt: 0,
    lastSnapshot: null,
    intentionalClose: false,
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
    timeZone: "America/Sao_Paulo",
  });

  function formatDateTimeToLocalBrazil(isoString) {
    if (!isoString) {
      return "—";
    }
    try {
      const date = new Date(isoString);
      if (isNaN(date.getTime())) {
        return isoString;
      }
      return dateTimeFormatter.format(date);
    } catch (e) {
      return isoString;
    }
  }

  function formatMoney(value) {
    if (value === null || value === undefined || value === "—") {
      return "—";
    }
    return moneyFormatter.format(Number(value));
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

  function renderSummary(summary) {
    elements.summaryExposure.textContent = formatMoney(summary.total_exposure_usdt);
    elements.summaryMargin.textContent = formatMoney(summary.total_margin_used_usdt);
    elements.summaryPnl.textContent = formatMoney(summary.total_unrealized_pnl_usdt);
    elements.lastUpdate.textContent = `Atualizado em ${formatDateTimeToLocalBrazil(summary.last_update_at)}`;
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

  function renderEmptyState() {
    elements.positionsBody.innerHTML = `
      <tr class="empty-row">
        <td colspan="10">Nenhuma posição aberta no momento.</td>
      </tr>
    `;
  }

  function renderPositions(positions) {
    if (!positions || positions.length === 0) {
      renderEmptyState();
      return;
    }

    elements.positionsBody.innerHTML = positions
      .map(
        (position) => `
          <tr>
            <td>${position.symbol}</td>
            <td>${position.side}</td>
            <td>${formatNumber(position.quantity)}</td>
            <td>${position.leverage}</td>
            <td>${formatMoney(position.entry_price)}</td>
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

    const delay = Math.min(5000, 500 * 2 ** state.reconnectAttempt);
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
    });

    socket.addEventListener("message", (event) => {
      const snapshot = JSON.parse(event.data);
      renderSnapshot(snapshot);
    });

    socket.addEventListener("close", () => {
      setStatus("offline");
      if (state.intentionalClose) {
        state.intentionalClose = false;
        return;
      }

      scheduleReconnect();
    });

    socket.addEventListener("error", () => {
      setStatus("offline");
    });
  }

  function bootstrap() {
    renderEmptyState();
    setStatus("offline");
    setBanner({ visible: false });
    connect();
  }

  document.addEventListener("DOMContentLoaded", bootstrap);
})();