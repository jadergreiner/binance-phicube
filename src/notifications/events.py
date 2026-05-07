"""
Eventos de notificação — contratos para alertas operacionais.

Define os tipos de eventos que podem gerar notificações e seus payloads.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class NotificationEvent(str, Enum):
    """Tipos de eventos que geram notificações."""

    TRADE_OPENED = "trade_opened"
    TRADE_CLOSED = "trade_closed"
    CRITICAL_ERROR = "critical_error"
    SL_PROTECTION_FAILED = "sl_protection_failed"
    PERFORMANCE_REPORT = "performance_report"
    SL_MISSING = "sl_missing"
    SL_RESTORED = "sl_restored"


@dataclass(frozen=True)
class TradeOpenedEvent:
    """Evento de trade aberto com sucesso."""

    symbol: str
    direction: str  # "long" ou "short"
    quantity: float
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_amount: float
    timestamp: datetime

    def to_message(self) -> str:
        """Converte o evento em mensagem formatada para Telegram."""
        direction_emoji = "🟢" if self.direction == "long" else "🔴"
        direction_text = "LONG" if self.direction == "long" else "SHORT"

        return f"""{direction_emoji} **TRADE ABERTO**

📊 **Símbolo:** {self.symbol}
📈 **Direção:** {direction_text}
💰 **Quantidade:** {self.quantity:.4f}
🎯 **Entrada:** ${self.entry_price:.2f}
🛡️ **Stop Loss:** ${self.stop_loss:.2f}
💎 **Take Profit:** ${self.take_profit:.2f}
⚠️ **Risco:** ${self.risk_amount:.2f}

⏰ {self.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"""


@dataclass(frozen=True)
class CriticalErrorEvent:
    """Evento de erro crítico na execução."""

    operation: str
    symbol: str | None
    error_message: str
    timestamp: datetime

    def to_message(self) -> str:
        """Converte o evento em mensagem formatada para Telegram."""
        symbol_info = f" ({self.symbol})" if self.symbol else ""

        return f"""🚨 **ERRO CRÍTICO**

⚙️ **Operação:** {self.operation}{symbol_info}
❌ **Erro:** {self.error_message}

⏰ {self.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"""


@dataclass(frozen=True)
class SLProtectionFailedEvent:
    """Evento de falha na proteção de stop loss após entrada."""

    symbol: str
    entry_order_id: str
    entry_price: float
    quantity: float
    timestamp: datetime

    def to_message(self) -> str:
        """Converte o evento em mensagem formatada para Telegram."""
        return f"""🚨 **PROTEÇÃO FALHADA**

⚠️ **STOP LOSS NÃO CONFIGURADO**
📊 **Símbolo:** {self.symbol}
🎯 **Preço Entrada:** ${self.entry_price:.2f}
💰 **Quantidade:** {self.quantity:.4f}
📋 **Order ID:** {self.entry_order_id}

**AÇÃO NECESSÁRIA:** Configure SL manualmente para proteger posição!

⏰ {self.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"""


@dataclass(frozen=True)
class SLMissingEvent:
    """Evento de SL cancelado ou ausente com posição aberta."""

    symbol: str
    trade_id: str
    sl_price: float
    current_price: float
    pct_distance: float
    timestamp: datetime
    notification_count: int = 1
    time_unprotected_seconds: int = 0

    def to_message(self) -> str:
        """Converte o evento em mensagem formatada para Telegram."""
        if self.notification_count > 1:
            mins = self.time_unprotected_seconds // 60
            header = f"🚨 **SL AUSENTE — Re-alerta #{self.notification_count}**"
            extra = f"\n⏳ **Desprotegido há:** {mins} minuto(s)"
        else:
            header = "🚨 **SL AUSENTE — AÇÃO NECESSÁRIA**"
            extra = ""

        return (
            f"{header}\n\n"
            f"📊 **Símbolo:** {self.symbol}\n"
            f"🛡️ **SL esperado:** ${self.sl_price:.4f}\n"
            f"📈 **Preço atual:** ${self.current_price:.4f}\n"
            f"📏 **Distância:** {self.pct_distance:.2f}%\n"
            f"🆔 **Trade ID:** {self.trade_id}"
            f"{extra}\n\n"
            f"**AÇÃO NECESSÁRIA:** Recoloque o Stop Loss manualmente!\n\n"
            f"⏰ {self.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )


@dataclass(frozen=True)
class SLRestoredEvent:
    """Evento informativo de SL restaurado ou posição encerrada após período órfão."""

    symbol: str
    trade_id: str
    response_time_seconds: int
    notification_count: int
    timestamp: datetime

    def to_message(self) -> str:
        """Converte o evento em mensagem formatada para Telegram."""
        mins = self.response_time_seconds // 60
        return (
            f"✅ **SL RESTAURADO**\n\n"
            f"📊 **Símbolo:** {self.symbol}\n"
            f"🆔 **Trade ID:** {self.trade_id}\n"
            f"⏱️ **Tempo de resposta:** {mins} minuto(s)\n"
            f"🔔 **Alertas enviados:** {self.notification_count}\n\n"
            f"⏰ {self.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )


@dataclass(frozen=True)
class PerformanceReportEvent:
    """Evento de relatório periódico de performance."""

    total_trades: int
    win_rate_pct: float
    total_pnl_usdt: float
    avg_rrr: float
    max_drawdown_usdt: float
    profit_factor: float
    timestamp: datetime

    def to_message(self) -> str:
        """Converte as métricas em mensagem formatada para Telegram."""
        if self.total_trades == 0:
            return (
                f"📊 *Relatório de Performance*\n"
                f"🕐 {self.timestamp.strftime('%Y-%m-%d %H:%M')} UTC\n\n"
                f"Nenhum trade fechado ainda."
            )

        pnl_sign = "+" if self.total_pnl_usdt >= 0 else ""
        return (
            f"📊 *Relatório de Performance*\n"
            f"🕐 {self.timestamp.strftime('%Y-%m-%d %H:%M')} UTC\n\n"
            f"Trades: {self.total_trades}\n"
            f"Win Rate: {self.win_rate_pct:.2f}%\n"
            f"P&L Total: {pnl_sign}{self.total_pnl_usdt:.2f} USDT\n"
            f"RRR Médio: {self.avg_rrr:.2f}\n"
            f"Max Drawdown: {self.max_drawdown_usdt:.2f} USDT\n"
            f"Profit Factor: {self.profit_factor:.2f}"
        )
