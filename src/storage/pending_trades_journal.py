"""
PendingTradesJournal — Persistência local de trades não-persistidos.

Gerencia arquivo `.pending_trades.jsonl` em `src/storage/` com:
- Idempotência (trade_id único)
- Append-only (sempre escreve ao final)
- Reprocessamento de trades não-persistidos no MongoDB
- Atomicidade de arquivo (sem corrupção parcial)

Sem logging direto — logging fica em quem chama.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from src.trading.order_manager import Trade


class PendingTradesJournal:
    """Gerencia persistência local de trades em arquivo .jsonl append-only."""

    def __init__(self, journal_path: str | Path | None = None) -> None:
        """
        Inicializa o journal.

        Args:
            journal_path: Caminho do arquivo .jsonl. Default: src/storage/.pending_trades.jsonl
        """
        if journal_path is None:
            # Default: arquivo no mesmo diretório que o repositório
            journal_path = Path(__file__).parent / ".pending_trades.jsonl"
        else:
            journal_path = Path(journal_path)

        self._journal_path = journal_path
        self._lock = asyncio.Lock()

    async def add_trade(self, trade: Trade) -> None:
        """
        Adiciona um trade ao journal de forma idempotente.

        Escreve uma linha JSON ao arquivo (append-only).
        Se trade_id (entry_order_id) já existe, ignora (não duplica).

        Args:
            trade: Trade a persistir localmente.
        """
        async with self._lock:
            trade_id = trade.entry_order_id

            # Lê trades existentes para verificar idempotência
            existing_ids = await self._read_trade_ids()
            if trade_id in existing_ids:
                # Já existe, ignora
                return

            # Converte Trade para dict e serializa
            trade_dict = trade.to_dict()
            line = json.dumps(trade_dict, default=str) + "\n"

            # Escreve de forma append-only (no final do arquivo)
            # Garante atomicidade via leitura do arquivo atual + append
            try:
                # Se arquivo não existe, cria; se existe, abre em append
                current_content = ""
                if self._journal_path.exists():
                    current_content = self._journal_path.read_text(encoding="utf-8")

                # Monta novo conteúdo (preserva existente)
                new_content = current_content + line

                # Escreve atomicamente via arquivo temporário
                temp_path = self._journal_path.with_suffix(".tmp")
                try:
                    temp_path.write_text(new_content, encoding="utf-8")
                    temp_path.replace(self._journal_path)
                except Exception:
                    temp_path.unlink(missing_ok=True)
                    raise
            except Exception:
                raise

    async def list_pending(self) -> list[Trade]:
        """
        Lista todos os trades pendentes no journal.

        Lê o arquivo .jsonl e retorna lista de Trade desserializados.

        Returns:
            Lista de Trade pendentes.
        """
        async with self._lock:
            if not self._journal_path.exists():
                return []

            trades: list[Trade] = []
            seen_ids: set[str] = set()

            try:
                content = self._journal_path.read_text(encoding="utf-8")
                for line in content.strip().split("\n"):
                    if not line.strip():
                        continue

                    try:
                        trade_dict = json.loads(line)
                        trade_id = trade_dict.get("entry_order_id")

                        # Ignora duplicatas (mantém apenas a primeira ocorrência)
                        if trade_id in seen_ids:
                            continue

                        seen_ids.add(trade_id)
                        trade = self._deserialize_trade(trade_dict)
                        trades.append(trade)
                    except (json.JSONDecodeError, ValueError):
                        # Linha mal-formatada, pula
                        continue

                return trades
            except FileNotFoundError:
                return []

    async def remove_trade(self, trade_id: str) -> None:
        """
        Remove um trade do journal pelo entry_order_id.

        Lê todas as linhas, filtra a correspondente, e reescreve o arquivo.
        Operação é segura contra corrupção via arquivo temporário.

        Args:
            trade_id: entry_order_id do trade a remover.
        """
        async with self._lock:
            if not self._journal_path.exists():
                return

            try:
                content = self._journal_path.read_text(encoding="utf-8")
                lines = content.split("\n")

                # Filtra linhas, removendo a que tem trade_id
                filtered_lines = []
                for line in lines:
                    if not line.strip():
                        # Preserva linhas vazias (se houver)
                        filtered_lines.append(line)
                        continue

                    try:
                        trade_dict = json.loads(line)
                        if trade_dict.get("entry_order_id") != trade_id:
                            filtered_lines.append(line)
                    except json.JSONDecodeError:
                        # Linha mal-formatada, mantém
                        filtered_lines.append(line)

                # Reescreve atomicamente
                new_content = "\n".join(filtered_lines)
                temp_path = self._journal_path.with_suffix(".tmp")
                try:
                    temp_path.write_text(new_content, encoding="utf-8")
                    temp_path.replace(self._journal_path)
                except Exception:
                    temp_path.unlink(missing_ok=True)
                    raise
            except FileNotFoundError:
                # Arquivo não existe, nada a fazer
                pass

    async def reprocess_pending_trades(
        self,
        mongo_repo: Any,
    ) -> tuple[int, int]:
        """
        Tenta reinsertar todos os trades pendentes no MongoDB.

        Remove do journal apenas se a reinserção for bem-sucedida.

        Args:
            mongo_repo: Repository com método save_trade() para persistir trades.

        Returns:
            Tupla (reprocessed_count, failed_count) de trades.
        """
        pending_trades = await self.list_pending()

        reprocessed = 0
        failed = 0

        for trade in pending_trades:
            try:
                # Tenta reinsertar no MongoDB
                await mongo_repo.save_trade(trade)
                # Se sucesso, remove do journal
                await self.remove_trade(trade.entry_order_id)
                reprocessed += 1
            except Exception:
                # Se falha, mantém no journal para próxima tentativa
                failed += 1

        return reprocessed, failed

    async def _read_trade_ids(self) -> set[str]:
        """
        Lê todos os trade_ids (entry_order_id) do journal.

        Retorna set vazio se arquivo não existe.

        Returns:
            Set de entry_order_id únicos no journal.
        """
        if not self._journal_path.exists():
            return set()

        trade_ids: set[str] = set()
        try:
            content = self._journal_path.read_text(encoding="utf-8")
            for line in content.strip().split("\n"):
                if not line.strip():
                    continue

                try:
                    trade_dict = json.loads(line)
                    trade_id = trade_dict.get("entry_order_id")
                    if trade_id:
                        trade_ids.add(trade_id)
                except json.JSONDecodeError:
                    continue

            return trade_ids
        except FileNotFoundError:
            return set()

    @staticmethod
    def _deserialize_trade(trade_dict: dict) -> Trade:
        """
        Desserializa um dicionário em Trade.

        Converte campos de volta para seus tipos originais
        (Direction, TradeStatus, ExitStrategy, datetime).

        Args:
            trade_dict: Dicionário com dados do trade.

        Returns:
            Trade desserializado.
        """
        from datetime import datetime

        from src.config.settings import ExitStrategy
        from src.strategy.signal_engine import Direction
        from src.trading.order_manager import Trade, TradeStatus

        # Converte strings de volta para enums
        direction = Direction(trade_dict.get("direction", "LONG"))
        status = TradeStatus(trade_dict.get("status", "OPEN"))

        exit_strategy = None
        if trade_dict.get("exit_strategy"):
            try:
                exit_strategy = ExitStrategy(trade_dict["exit_strategy"])
            except (ValueError, KeyError):
                exit_strategy = None

        # Converte strings ISO 8601 de volta para datetime
        opened_at_str = trade_dict.get("opened_at")
        if isinstance(opened_at_str, str):
            try:
                opened_at = datetime.fromisoformat(opened_at_str.replace("Z", "+00:00"))
            except ValueError:
                from datetime import UTC

                opened_at = datetime.now(UTC)
        else:
            from datetime import UTC

            opened_at = opened_at_str or datetime.now(UTC)

        closed_at = None
        closed_at_str = trade_dict.get("closed_at")
        if isinstance(closed_at_str, str):
            try:
                closed_at = datetime.fromisoformat(closed_at_str.replace("Z", "+00:00"))
            except ValueError:
                closed_at = None

        return Trade(
            symbol=trade_dict.get("symbol", ""),
            timeframe=trade_dict.get("timeframe", ""),
            direction=direction,
            quantity=float(trade_dict.get("quantity", 0.0)),
            entry_price=float(trade_dict.get("entry_price", 0.0)),
            stop_loss=float(trade_dict.get("stop_loss", 0.0)),
            take_profit=float(trade_dict.get("take_profit", 0.0)),
            risk_amount=float(trade_dict.get("risk_amount", 0.0)),
            margin_used=float(trade_dict.get("margin_used", 0.0)),
            entry_order_id=trade_dict.get("entry_order_id", ""),
            sl_order_id=trade_dict.get("sl_order_id"),
            tp_order_id=trade_dict.get("tp_order_id"),
            status=status,
            opened_at=opened_at,
            closed_at=closed_at,
            pnl=trade_dict.get("pnl"),
            exit_price=trade_dict.get("exit_price"),
            pnl_usdt=trade_dict.get("pnl_usdt"),
            close_reason=trade_dict.get("close_reason"),
            signal=trade_dict.get("signal", {}),
            exit_strategy=exit_strategy,
            tp_levels=trade_dict.get("tp_levels"),
            tp_order_ids=trade_dict.get("tp_order_ids"),
        )
