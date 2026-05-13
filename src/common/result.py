"""
Result/Monad Pattern para Tratamento Tipado de Erros

Implementa o padrão Result para tratamento de erros tipado, eliminando
retornos None e estado externo para controle de fluxo.

Baseado no padrão Result do Rust e outras linguagens funcionais.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, Generic, TypeVar

T = TypeVar("T")
U = TypeVar("U")
E = TypeVar("E")


class Result(Generic[T, E], ABC):
    """
    Tipo Result genérico para tratamento de erros tipado.

    Representa um valor que pode ser um sucesso (Ok) ou um erro (Err).
    Elimina a necessidade de retornos None e controle de fluxo externo.
    """

    @abstractmethod
    def is_ok(self) -> bool:
        """Retorna True se o Result é Ok."""
        pass

    @abstractmethod
    def is_err(self) -> bool:
        """Retorna True se o Result é Err."""
        pass

    @abstractmethod
    def map(self, fn: Callable[[T], U]) -> Result[U, E]:
        """
        Aplica uma função ao valor se Ok, caso contrário propaga o erro.

        Args:
            fn: Função a ser aplicada ao valor

        Returns:
            Result[U, E]: Novo Result com valor transformado ou erro propagado
        """
        pass

    @abstractmethod
    def flat_map(self, fn: Callable[[T], Result[U, E]]) -> Result[U, E]:
        """
        Aplica uma função que retorna Result ao valor se Ok.
        Permite composição de operações que podem falhar.

        Args:
            fn: Função que retorna Result

        Returns:
            Result[U, E]: Result retornado pela função ou erro propagado
        """
        pass

    @abstractmethod
    def unwrap(self) -> T:
        """
        Extrai o valor se Ok, caso contrário levanta exceção.

        Returns:
            T: Valor contido no Ok

        Raises:
            ValueError: Se o Result é Err
        """
        pass

    @abstractmethod
    def unwrap_or(self, default: T) -> T:
        """
        Extrai o valor se Ok, caso contrário retorna valor padrão.

        Args:
            default: Valor padrão a retornar se Err

        Returns:
            T: Valor contido no Ok ou valor padrão
        """
        pass

    @abstractmethod
    def expect(self, msg: str) -> T:
        """
        Extrai o valor se Ok, caso contrário levanta exceção com mensagem.

        Args:
            msg: Mensagem de erro personalizada

        Returns:
            T: Valor contido no Ok

        Raises:
            ValueError: Se o Result é Err, com mensagem personalizada
        """
        pass

    @abstractmethod
    def unwrap_err(self) -> E:
        """
        Extrai o erro se Err, caso contrário levanta exceção.

        Returns:
            E: Erro contido no Err

        Raises:
            ValueError: Se o Result é Ok
        """
        pass


class Ok(Result[T, E]):
    """Variant Ok do Result - representa sucesso."""

    def __init__(self, value: T) -> None:
        self.value = value

    def is_ok(self) -> bool:
        return True

    def is_err(self) -> bool:
        return False

    def map(self, fn: Callable[[T], U]) -> Result[U, E]:
        try:
            return Ok(fn(self.value))
        except Exception as e:
            # Se a função falhar, retorna Err
            return Err(e)  # type: ignore

    def flat_map(self, fn: Callable[[T], Result[U, E]]) -> Result[U, E]:
        try:
            return fn(self.value)
        except Exception as e:
            return Err(e)  # type: ignore

    def unwrap(self) -> T:
        return self.value

    def unwrap_or(self, default: T) -> T:
        return self.value

    def expect(self, msg: str) -> T:
        return self.value

    def unwrap_err(self) -> E:
        raise ValueError(f"Tentativa de unwrap_err em Ok: {self.value}")

    def __repr__(self) -> str:
        return f"Ok({self.value!r})"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Ok) and self.value == other.value


class Err(Result[T, E]):
    """Variant Err do Result - representa erro."""

    def __init__(self, error: E) -> None:
        self.error = error

    def is_ok(self) -> bool:
        return False

    def is_err(self) -> bool:
        return True

    def map(self, fn: Callable[[T], U]) -> Result[U, E]:
        return Err(self.error)

    def flat_map(self, fn: Callable[[T], Result[U, E]]) -> Result[U, E]:
        return Err(self.error)

    def unwrap(self) -> T:
        raise ValueError(f"Tentativa de unwrap em Err: {self.error}")

    def unwrap_or(self, default: T) -> T:
        return default

    def expect(self, msg: str) -> T:
        raise ValueError(f"{msg}: {self.error}")

    def unwrap_err(self) -> E:
        return self.error

    def __repr__(self) -> str:
        return f"Err({self.error!r})"

    def __eq__(self, other: Any) -> bool:
        return isinstance(other, Err) and self.error == other.error


# Funções auxiliares para criação de Results
def ok(value: T) -> Result[T, Any]:
    """Cria um Result Ok com o valor fornecido."""
    return Ok(value)


def err(error: E) -> Result[Any, E]:
    """Cria um Result Err com o erro fornecido."""
    return Err(error)


# Tipos de erro específicos para o domínio
class RiskRejection:
    """Erro específico para rejeição de risco."""

    def __init__(self, code: str, reason: str, details: dict[str, Any] | None = None) -> None:
        self.code = code
        self.reason = reason
        self.details = details or {}

    def __repr__(self) -> str:
        return f"RiskRejection(code='{self.code}', reason='{self.reason}', details={self.details})"

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, RiskRejection)
            and self.code == other.code
            and self.reason == other.reason
            and self.details == other.details
        )


class OrderError:
    """Erro específico para falhas de ordem."""

    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        self.code = code
        self.message = message
        self.details = details or {}

    def __repr__(self) -> str:
        return f"OrderError(code='{self.code}', message='{self.message}', details={self.details})"

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, OrderError)
            and self.code == other.code
            and self.message == other.message
            and self.details == other.details
        )


class SignalError:
    """Erro específico para falhas de sinal."""

    def __init__(self, type: str, message: str, context: dict[str, Any] | None = None) -> None:
        self.type = type
        self.message = message
        self.context = context or {}

    def __repr__(self) -> str:
        return f"SignalError(type='{self.type}', message='{self.message}', context={self.context})"

    def __eq__(self, other: Any) -> bool:
        return (
            isinstance(other, SignalError)
            and self.type == other.type
            and self.message == other.message
            and self.context == other.context
        )
