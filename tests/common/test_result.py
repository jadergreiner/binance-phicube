"""
Testes para o módulo Result/Monad Pattern.

Testa todas as funcionalidades do tipo Result incluindo:
- Variants Ok e Err
- Métodos de transformação (map, flat_map)
- Métodos de extração (unwrap, unwrap_or, expect)
- Composição de Results (flat_map chain)
"""

import pytest

from src.common.result import Err, Ok, OrderError, Result, RiskRejection, SignalError, err, ok


class TestResultBasics:
    """Testa funcionalidades básicas do Result."""

    def test_ok_creation(self):
        """Testa criação de Ok."""
        result = Ok(42)
        assert result.is_ok()
        assert not result.is_err()
        assert result.unwrap() == 42

    def test_err_creation(self):
        """Testa criação de Err."""
        result = Err("erro")
        assert not result.is_ok()
        assert result.is_err()
        assert isinstance(result, Err)
        assert result.error == "erro"

    def test_ok_helper(self):
        """Testa função helper ok()."""
        result = ok(42)
        assert isinstance(result, Ok)
        assert result.unwrap() == 42

    def test_err_helper(self):
        """Testa função helper err()."""
        result = err("erro")
        assert isinstance(result, Err)
        assert result.error == "erro"


class TestResultMap:
    """Testa método map do Result."""

    def test_ok_map(self):
        """Testa map em Ok."""
        result = Ok(5)
        mapped = result.map(lambda x: x * 2)
        assert mapped.is_ok()
        assert mapped.unwrap() == 10

    def test_err_map(self):
        """Testa map em Err - deve propagar erro."""
        result = Err("erro")
        mapped = result.map(lambda x: x * 2)
        assert mapped.is_err()
        assert isinstance(mapped, Err)
        assert mapped.error == "erro"

    def test_ok_map_with_exception(self):
        """Testa map em Ok quando função levanta exceção."""
        result = Ok(5)
        mapped = result.map(lambda x: x / 0)  # ZeroDivisionError
        assert mapped.is_err()
        assert isinstance(mapped, Err)
        assert isinstance(mapped.error, ZeroDivisionError)


class TestResultFlatMap:
    """Testa método flat_map do Result."""

    def test_ok_flat_map_ok(self):
        """Testa flat_map em Ok que retorna Ok."""
        result = Ok(5)
        flat_mapped = result.flat_map(lambda x: Ok(x * 2))
        assert flat_mapped.is_ok()
        assert flat_mapped.unwrap() == 10

    def test_ok_flat_map_err(self):
        """Testa flat_map em Ok que retorna Err."""
        result = Ok(5)
        flat_mapped = result.flat_map(lambda x: Err("erro na função"))
        assert flat_mapped.is_err()
        assert isinstance(flat_mapped, Err)
        assert flat_mapped.error == "erro na função"

    def test_err_flat_map(self):
        """Testa flat_map em Err - deve propagar erro."""
        result = Err("erro original")
        flat_mapped = result.flat_map(lambda x: Ok(x * 2))
        assert flat_mapped.is_err()
        assert isinstance(flat_mapped, Err)
        assert flat_mapped.error == "erro original"

    def test_flat_map_chain(self):
        """Testa composição de flat_maps (chain)."""

        def add_one(x: int) -> Result[int, str]:
            return Ok(x + 1)

        def multiply_two(x: int) -> Result[int, str]:
            return Ok(x * 2)

        def fail_if_greater_than_ten(x: int) -> Result[int, str]:
            if x > 10:
                return Err("valor muito grande")
            return Ok(x)

        # Chain que deve funcionar: 5 -> 6 -> 12 -> erro
        result = Ok(5).flat_map(add_one).flat_map(multiply_two).flat_map(fail_if_greater_than_ten)

        assert result.is_err()
        assert isinstance(result, Err)
        assert result.error == "valor muito grande"

        # Chain que deve funcionar: 2 -> 3 -> 6 -> 6
        result = Ok(2).flat_map(add_one).flat_map(multiply_two).flat_map(fail_if_greater_than_ten)

        assert result.is_ok()
        assert result.unwrap() == 6


class TestResultUnwrap:
    """Testa métodos de extração do Result."""

    def test_ok_unwrap(self):
        """Testa unwrap em Ok."""
        result = Ok(42)
        assert result.unwrap() == 42

    def test_err_unwrap_raises(self):
        """Testa unwrap em Err - deve levantar exceção."""
        result = Err("erro")
        with pytest.raises(ValueError, match="Tentativa de unwrap em Err: erro"):
            result.unwrap()

    def test_ok_unwrap_or(self):
        """Testa unwrap_or em Ok."""
        result = Ok(42)
        assert result.unwrap_or(0) == 42

    def test_err_unwrap_or(self):
        """Testa unwrap_or em Err - deve retornar default."""
        result = Err("erro")
        assert result.unwrap_or(0) == 0

    def test_ok_expect(self):
        """Testa expect em Ok."""
        result = Ok(42)
        assert result.expect("deveria ter valor") == 42

    def test_err_expect_raises(self):
        """Testa expect em Err - deve levantar exceção com mensagem."""
        result = Err("erro")
        with pytest.raises(ValueError, match="deveria ter valor: erro"):
            result.expect("deveria ter valor")


class TestResultEquality:
    """Testa igualdade entre Results."""

    def test_ok_equality(self):
        """Testa igualdade entre Oks."""
        assert Ok(42) == Ok(42)
        assert Ok(42) != Ok(43)
        assert Ok(42) != Err("erro")

    def test_err_equality(self):
        """Testa igualdade entre Errs."""
        assert Err("erro") == Err("erro")
        assert Err("erro1") != Err("erro2")
        assert Err("erro") != Ok(42)


class TestResultRepr:
    """Testa representação string dos Results."""

    def test_ok_repr(self):
        """Testa repr de Ok."""
        result = Ok(42)
        assert repr(result) == "Ok(42)"

    def test_err_repr(self):
        """Testa repr de Err."""
        result = Err("erro")
        assert repr(result) == "Err('erro')"


class TestDomainErrors:
    """Testa tipos de erro específicos do domínio."""

    def test_risk_rejection(self):
        """Testa RiskRejection."""
        rejection = RiskRejection("saldo insuficiente", {"balance": 100, "required": 200})
        assert rejection.reason == "saldo insuficiente"
        assert rejection.details["balance"] == 100
        assert rejection.details["required"] == 200

        # Teste de igualdade
        rejection2 = RiskRejection("saldo insuficiente", {"balance": 100, "required": 200})
        assert rejection == rejection2

        # Teste de repr
        expected_repr = (
            "RiskRejection(reason='saldo insuficiente', details={'balance': 100, 'required': 200})"
        )
        assert repr(rejection) == expected_repr

    def test_order_error(self):
        """Testa OrderError."""
        error = OrderError("INSUFFICIENT_BALANCE", "Saldo insuficiente", {"balance": 100})
        assert error.code == "INSUFFICIENT_BALANCE"
        assert error.message == "Saldo insuficiente"
        assert error.details["balance"] == 100

        # Teste de igualdade
        error2 = OrderError("INSUFFICIENT_BALANCE", "Saldo insuficiente", {"balance": 100})
        assert error == error2

        # Teste de repr
        expected_repr = "OrderError(code='INSUFFICIENT_BALANCE', message='Saldo insuficiente', details={'balance': 100})"
        assert repr(error) == expected_repr

    def test_signal_error(self):
        """Testa SignalError."""
        error = SignalError("INVALID_TIMEFRAME", "Timeframe não suportado", {"timeframe": "1s"})
        assert error.type == "INVALID_TIMEFRAME"
        assert error.message == "Timeframe não suportado"
        assert error.context["timeframe"] == "1s"

        # Teste de igualdade
        error2 = SignalError("INVALID_TIMEFRAME", "Timeframe não suportado", {"timeframe": "1s"})
        assert error == error2

        # Teste de repr
        expected_repr = "SignalError(type='INVALID_TIMEFRAME', message='Timeframe não suportado', context={'timeframe': '1s'})"
        assert repr(error) == expected_repr


class TestResultIntegration:
    """Testa integração e casos de uso reais."""

    def test_risk_calculation_simulation(self):
        """Simula cálculo de risco usando Result."""

        def calculate_position_size(
            balance: float, risk_pct: float
        ) -> Result[float, RiskRejection]:
            if balance <= 0:
                return Err(RiskRejection("saldo inválido", {"balance": balance}))

            if risk_pct <= 0 or risk_pct > 100:
                return Err(RiskRejection("percentual de risco inválido", {"risk_pct": risk_pct}))

            position_size = balance * (risk_pct / 100)
            return Ok(position_size)

        # Caso de sucesso
        result = calculate_position_size(1000.0, 2.0)
        assert result.is_ok()
        assert result.unwrap() == 20.0

        # Caso de erro - saldo inválido
        result = calculate_position_size(-100.0, 2.0)
        assert result.is_err()
        assert isinstance(result, Err)
        assert result.error.reason == "saldo inválido"

        # Caso de erro - risco inválido
        result = calculate_position_size(1000.0, 150.0)
        assert result.is_err()
        assert isinstance(result, Err)
        assert result.error.reason == "percentual de risco inválido"

    def test_order_execution_simulation(self):
        """Simula execução de ordem usando Result."""

        def execute_order(symbol: str, quantity: float) -> Result[str, OrderError]:
            if not symbol:
                return Err(OrderError("INVALID_SYMBOL", "Símbolo não pode ser vazio"))

            if quantity <= 0:
                return Err(
                    OrderError(
                        "INVALID_QUANTITY", "Quantidade deve ser positiva", {"quantity": quantity}
                    )
                )

            # Simula execução bem-sucedida
            order_id = f"ORDER_{symbol}_{int(quantity * 1000)}"
            return Ok(order_id)

        # Caso de sucesso
        result = execute_order("BTCUSDT", 0.001)
        assert result.is_ok()
        assert result.unwrap() == "ORDER_BTCUSDT_1"

        # Caso de erro - símbolo inválido
        result = execute_order("", 0.001)
        assert result.is_err()
        assert isinstance(result, Err)
        assert result.error.code == "INVALID_SYMBOL"

        # Caso de erro - quantidade inválida
        result = execute_order("BTCUSDT", -0.001)
        assert result.is_err()
        assert isinstance(result, Err)
        assert result.error.code == "INVALID_QUANTITY"

    def test_complex_chain_simulation(self):
        """Simula chain complexo de operações usando Result."""

        def validate_symbol(symbol: str) -> Result[str, str]:
            if not symbol or len(symbol) < 6:
                return Err("símbolo inválido")
            return Ok(symbol)

        def get_price(symbol: str) -> Result[float, str]:
            # Simula busca de preço
            if symbol == "BTCUSDT":
                return Ok(50000.0)
            return Err("preço não encontrado")

        def calculate_value(price: float) -> Result[float, str]:
            quantity = 0.001
            value = price * quantity
            if value < 10:  # Valor mínimo
                return Err("valor muito baixo")
            return Ok(value)

        # Chain de sucesso
        result = (
            Ok("BTCUSDT").flat_map(validate_symbol).flat_map(get_price).flat_map(calculate_value)
        )

        assert result.is_ok()
        assert result.unwrap() == 50.0

        # Chain com falha na validação
        result = Ok("BTC").flat_map(validate_symbol).flat_map(get_price).flat_map(calculate_value)

        assert result.is_err()
        assert isinstance(result, Err)
        assert result.error == "símbolo inválido"

        # Chain com falha no preço
        result = (
            Ok("ETHUSDT").flat_map(validate_symbol).flat_map(get_price).flat_map(calculate_value)
        )

        assert result.is_err()
        assert isinstance(result, Err)
        assert result.error == "preço não encontrado"
