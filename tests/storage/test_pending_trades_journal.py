"""
Testes para PendingTradesJournal.

Cobre:
- Idempotência (add_trade com mesma trade_id)
- Persistência de arquivo .jsonl
- Leitura e desserialização de trades
- Remoção segura sem corrupção
- Reprocessamento com MongoDB
- Atomicidade de operações
"""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from src.storage.pending_trades_journal import PendingTradesJournal
from src.strategy.signal_engine import Direction
from src.trading.order_manager import Trade, TradeStatus


@pytest.fixture
def temp_journal_path():
    """Cria arquivo temporário para journal."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
    ) as f:
        path = Path(f.name)
    yield path
    path.unlink(missing_ok=True)
    path.with_suffix(".tmp").unlink(missing_ok=True)


@pytest.fixture
def sample_trade():
    """Trade de exemplo para testes."""
    return Trade(
        symbol="BTCUSDT",
        timeframe="15m",
        direction=Direction.LONG,
        quantity=0.5,
        entry_price=45000.0,
        stop_loss=44000.0,
        take_profit=46000.0,
        risk_amount=500.0,
        margin_used=1000.0,
        entry_order_id="order_123",
        sl_order_id="sl_456",
        tp_order_id="tp_789",
        status=TradeStatus.OPEN,
        signal={"alligator": "aligned", "ao": 100},
    )


@pytest.fixture
def journal(temp_journal_path):
    """Instancia PendingTradesJournal com arquivo temporário."""
    return PendingTradesJournal(temp_journal_path)


# ============================================================================
# Testes de add_trade (escrita)
# ============================================================================


@pytest.mark.asyncio
async def test_add_trade_writes_json_line(journal, sample_trade):
    """add_trade escreve linha JSON ao arquivo."""
    await journal.add_trade(sample_trade)

    content = journal._journal_path.read_text(encoding="utf-8")
    lines = content.strip().split("\n")

    assert len(lines) == 1
    trade_dict = json.loads(lines[0])
    assert trade_dict["entry_order_id"] == "order_123"
    assert trade_dict["symbol"] == "BTCUSDT"


@pytest.mark.asyncio
async def test_add_trade_is_idempotent(journal, sample_trade):
    """add_trade idempotente: mesma trade_id não duplica."""
    await journal.add_trade(sample_trade)
    await journal.add_trade(sample_trade)

    content = journal._journal_path.read_text(encoding="utf-8")
    lines = [line for line in content.strip().split("\n") if line.strip()]

    assert len(lines) == 1, "Não deve duplicar a mesma trade_id"


@pytest.mark.asyncio
async def test_add_trade_multiple_different_trades(journal, sample_trade):
    """add_trade adiciona múltiplos trades diferentes."""
    trade2 = Trade(
        symbol="ETHUSDT",
        timeframe="15m",
        direction=Direction.SHORT,
        quantity=1.0,
        entry_price=2500.0,
        stop_loss=2600.0,
        take_profit=2400.0,
        risk_amount=100.0,
        margin_used=500.0,
        entry_order_id="order_999",
    )

    await journal.add_trade(sample_trade)
    await journal.add_trade(trade2)

    content = journal._journal_path.read_text(encoding="utf-8")
    lines = [line for line in content.strip().split("\n") if line.strip()]

    assert len(lines) == 2


# ============================================================================
# Testes de list_pending (leitura)
# ============================================================================


@pytest.mark.asyncio
async def test_list_pending_empty_journal(journal):
    """list_pending retorna lista vazia se journal não existe."""
    trades = await journal.list_pending()
    assert trades == []


@pytest.mark.asyncio
async def test_list_pending_reads_trades(journal, sample_trade):
    """list_pending lê e desserializa trades corretamente."""
    await journal.add_trade(sample_trade)

    trades = await journal.list_pending()

    assert len(trades) == 1
    trade = trades[0]
    assert trade.symbol == "BTCUSDT"
    assert trade.entry_order_id == "order_123"
    assert trade.direction == Direction.LONG
    assert trade.status == TradeStatus.OPEN


@pytest.mark.asyncio
async def test_list_pending_multiple_trades(journal, sample_trade):
    """list_pending retorna múltiplos trades."""
    trade2 = Trade(
        symbol="ETHUSDT",
        timeframe="15m",
        direction=Direction.SHORT,
        quantity=1.0,
        entry_price=2500.0,
        stop_loss=2600.0,
        take_profit=2400.0,
        risk_amount=100.0,
        margin_used=500.0,
        entry_order_id="order_999",
    )

    await journal.add_trade(sample_trade)
    await journal.add_trade(trade2)

    trades = await journal.list_pending()

    assert len(trades) == 2
    symbols = {t.symbol for t in trades}
    assert symbols == {"BTCUSDT", "ETHUSDT"}


@pytest.mark.asyncio
async def test_list_pending_skips_malformed_json(journal, sample_trade):
    """list_pending ignora linhas com JSON mal-formatado."""
    await journal.add_trade(sample_trade)

    # Adiciona linha corrompida manualmente
    with open(journal._journal_path, "a", encoding="utf-8") as f:
        f.write("\ninvalid json line\n")

    trades = await journal.list_pending()

    # Deve retornar apenas o trade válido
    assert len(trades) == 1
    assert trades[0].entry_order_id == "order_123"


@pytest.mark.asyncio
async def test_list_pending_deduplicates_by_trade_id(journal, sample_trade):
    """list_pending mantém apenas primeira ocorrência de trade_id duplicado."""
    # Adiciona mesmo trade_id duas vezes manualmente (simula corrupção)
    trade_dict = sample_trade.to_dict()
    with open(journal._journal_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(trade_dict, default=str) + "\n")
        f.write(json.dumps(trade_dict, default=str) + "\n")

    trades = await journal.list_pending()

    assert len(trades) == 1
    assert trades[0].entry_order_id == "order_123"


# ============================================================================
# Testes de remove_trade (remoção segura)
# ============================================================================


@pytest.mark.asyncio
async def test_remove_trade_nonexistent_journal(journal):
    """remove_trade não falha se journal não existe."""
    # Não deve lançar exceção
    await journal.remove_trade("order_123")


@pytest.mark.asyncio
async def test_remove_trade_removes_exactly_one_line(journal, sample_trade):
    """remove_trade remove exatamente uma linha sem corromper arquivo."""
    await journal.add_trade(sample_trade)

    trade2 = Trade(
        symbol="ETHUSDT",
        timeframe="15m",
        direction=Direction.SHORT,
        quantity=1.0,
        entry_price=2500.0,
        stop_loss=2600.0,
        take_profit=2400.0,
        risk_amount=100.0,
        margin_used=500.0,
        entry_order_id="order_999",
    )
    await journal.add_trade(trade2)

    # Remove apenas o primeiro
    await journal.remove_trade("order_123")

    trades = await journal.list_pending()
    assert len(trades) == 1
    assert trades[0].entry_order_id == "order_999"


@pytest.mark.asyncio
async def test_remove_trade_preserves_remaining(journal, sample_trade):
    """remove_trade preserva estrutura do arquivo após remoção."""
    trade1 = sample_trade
    trade2 = Trade(
        symbol="ETHUSDT",
        timeframe="15m",
        direction=Direction.SHORT,
        quantity=1.0,
        entry_price=2500.0,
        stop_loss=2600.0,
        take_profit=2400.0,
        risk_amount=100.0,
        margin_used=500.0,
        entry_order_id="order_999",
    )
    trade3 = Trade(
        symbol="XRPUSDT",
        timeframe="15m",
        direction=Direction.LONG,
        quantity=10.0,
        entry_price=1.0,
        stop_loss=0.9,
        take_profit=1.1,
        risk_amount=10.0,
        margin_used=100.0,
        entry_order_id="order_111",
    )

    await journal.add_trade(trade1)
    await journal.add_trade(trade2)
    await journal.add_trade(trade3)

    # Remove do meio
    await journal.remove_trade("order_999")

    trades = await journal.list_pending()
    assert len(trades) == 2
    trade_ids = {t.entry_order_id for t in trades}
    assert trade_ids == {"order_123", "order_111"}


@pytest.mark.asyncio
async def test_remove_trade_nonexistent_id(journal, sample_trade):
    """remove_trade silenciosamente ignora trade_id inexistente."""
    await journal.add_trade(sample_trade)

    # Remove id que não existe
    await journal.remove_trade("order_nonexistent")

    # Trade original deve continuar
    trades = await journal.list_pending()
    assert len(trades) == 1
    assert trades[0].entry_order_id == "order_123"


# ============================================================================
# Testes de reprocess_pending_trades
# ============================================================================


@pytest.mark.asyncio
async def test_reprocess_pending_trades_success(journal, sample_trade):
    """reprocess reinsertar e remove do journal se sucesso."""
    await journal.add_trade(sample_trade)

    # Mock do mongo_repo
    mock_repo = AsyncMock()
    mock_repo.save_trade = AsyncMock()

    reprocessed, failed = await journal.reprocess_pending_trades(mock_repo)

    assert reprocessed == 1
    assert failed == 0
    mock_repo.save_trade.assert_called_once()

    # Verifica se removeu do journal
    trades = await journal.list_pending()
    assert len(trades) == 0


@pytest.mark.asyncio
async def test_reprocess_pending_trades_partial_failure(journal, sample_trade):
    """reprocess mantém trades que falharam, remove sucesso."""
    trade2 = Trade(
        symbol="ETHUSDT",
        timeframe="15m",
        direction=Direction.SHORT,
        quantity=1.0,
        entry_price=2500.0,
        stop_loss=2600.0,
        take_profit=2400.0,
        risk_amount=100.0,
        margin_used=500.0,
        entry_order_id="order_999",
    )

    await journal.add_trade(sample_trade)
    await journal.add_trade(trade2)

    # Mock do mongo_repo: primeiro falha, segundo sucesso
    mock_repo = AsyncMock()

    async def side_effect(trade):
        if trade.entry_order_id == "order_123":
            raise Exception("MongoDB connection failed")

    mock_repo.save_trade = AsyncMock(side_effect=side_effect)

    reprocessed, failed = await journal.reprocess_pending_trades(mock_repo)

    assert reprocessed == 1
    assert failed == 1

    # Verifica se removeu apenas o que sucesso
    trades = await journal.list_pending()
    assert len(trades) == 1
    assert trades[0].entry_order_id == "order_123"


@pytest.mark.asyncio
async def test_reprocess_pending_trades_all_fail(journal, sample_trade):
    """reprocess mantém todos os trades se todos falharem."""
    await journal.add_trade(sample_trade)

    mock_repo = AsyncMock()
    mock_repo.save_trade = AsyncMock(
        side_effect=Exception("MongoDB unavailable")
    )

    reprocessed, failed = await journal.reprocess_pending_trades(mock_repo)

    assert reprocessed == 0
    assert failed == 1

    # Verifica se manteve no journal
    trades = await journal.list_pending()
    assert len(trades) == 1


# ============================================================================
# Testes de Desserialização
# ============================================================================


@pytest.mark.asyncio
async def test_deserialize_preserves_datetime(journal):
    """Desserialização converte datetime strings corretamente."""
    # Cria trade com opened_at/closed_at específicos
    now = datetime.now(UTC)
    trade = Trade(
        symbol="BTCUSDT",
        timeframe="15m",
        direction=Direction.LONG,
        quantity=0.5,
        entry_price=45000.0,
        stop_loss=44000.0,
        take_profit=46000.0,
        risk_amount=500.0,
        margin_used=1000.0,
        entry_order_id="order_123",
        opened_at=now,
        status=TradeStatus.OPEN,
    )

    await journal.add_trade(trade)
    trades = await journal.list_pending()

    assert len(trades) == 1
    assert trades[0].opened_at.year == now.year
    assert trades[0].opened_at.month == now.month
    assert trades[0].opened_at.day == now.day


@pytest.mark.asyncio
async def test_deserialize_handles_missing_optional_fields(journal):
    """Desserialização preenche campos opcionais com defaults."""
    trade = Trade(
        symbol="BTCUSDT",
        timeframe="15m",
        direction=Direction.LONG,
        quantity=0.5,
        entry_price=45000.0,
        stop_loss=44000.0,
        take_profit=46000.0,
        risk_amount=500.0,
        margin_used=1000.0,
        entry_order_id="order_123",
        # sl_order_id, tp_order_id, status, etc. omitidos
    )

    await journal.add_trade(trade)
    trades = await journal.list_pending()

    assert len(trades) == 1
    assert trades[0].sl_order_id is None
    assert trades[0].tp_order_id is None
    assert trades[0].status == TradeStatus.OPEN


@pytest.mark.asyncio
async def test_deserialize_direction_enum(journal):
    """Desserialização converte Direction string para enum."""
    trade_short = Trade(
        symbol="BTCUSDT",
        timeframe="15m",
        direction=Direction.SHORT,
        quantity=0.5,
        entry_price=45000.0,
        stop_loss=46000.0,
        take_profit=44000.0,
        risk_amount=500.0,
        margin_used=1000.0,
        entry_order_id="order_short",
    )

    await journal.add_trade(trade_short)
    trades = await journal.list_pending()

    assert trades[0].direction == Direction.SHORT


# ============================================================================
# Testes de Atomicidade e Concorrência
# ============================================================================


@pytest.mark.asyncio
async def test_add_trade_uses_lock(journal, sample_trade):
    """add_trade usa lock para evitar race conditions."""
    # Verifica que lock existe
    assert journal._lock is not None

    # Adiciona dois trades "simultaneamente"
    await journal.add_trade(sample_trade)

    trade2 = Trade(
        symbol="ETHUSDT",
        timeframe="15m",
        direction=Direction.SHORT,
        quantity=1.0,
        entry_price=2500.0,
        stop_loss=2600.0,
        take_profit=2400.0,
        risk_amount=100.0,
        margin_used=500.0,
        entry_order_id="order_999",
    )

    # Simula concorrência
    import asyncio

    await asyncio.gather(
        journal.add_trade(trade2),
        journal.list_pending(),
    )

    # Nenhuma exceção deve ser lançada
    assert True


@pytest.mark.asyncio
async def test_temp_file_cleanup_on_error(journal, sample_trade, tmp_path):
    """Se escrita falhar, arquivo temporário é limpo."""
    journal._journal_path = tmp_path / "readonly" / ".pending_trades.jsonl"

    # Tenta adicionar trade em diretório que não existe
    with pytest.raises(Exception):
        await journal.add_trade(sample_trade)

    # Verifica se arquivo temporário foi limpo
    temp_path = journal._journal_path.with_suffix(".tmp")
    assert not temp_path.exists()


# ============================================================================
# Testes de Integração
# ============================================================================


@pytest.mark.asyncio
async def test_full_workflow(journal, sample_trade):
    """Workflow completo: add → list → remove → list."""
    # Add
    await journal.add_trade(sample_trade)
    trades = await journal.list_pending()
    assert len(trades) == 1

    # List
    retrieved = trades[0]
    assert retrieved.symbol == "BTCUSDT"

    # Remove
    await journal.remove_trade("order_123")
    trades = await journal.list_pending()
    assert len(trades) == 0


@pytest.mark.asyncio
async def test_multiple_journals_separate_files(sample_trade, temp_journal_path):
    """Múltiplos journals com arquivos separados não interferem."""
    path1 = temp_journal_path
    path2 = temp_journal_path.with_stem(".pending_trades_2")

    journal1 = PendingTradesJournal(path1)
    journal2 = PendingTradesJournal(path2)

    try:
        await journal1.add_trade(sample_trade)

        trades1 = await journal1.list_pending()
        trades2 = await journal2.list_pending()

        assert len(trades1) == 1
        assert len(trades2) == 0
    finally:
        path2.unlink(missing_ok=True)
