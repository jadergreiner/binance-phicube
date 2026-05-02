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

  function formatMoney(value) {
    if (value === null || value === undefined || value === "—") {
      return "—";
    }
    return moneyFormatter.format(Number(value));
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
    elements.lastUpdate.textContent = `Atualizado em ${summary.last_update_at}`;
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