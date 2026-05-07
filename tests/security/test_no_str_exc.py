"""Teste de auditoria de segurança: ausência de str(exc) em except blocks.

Garante que nenhum módulo em src/ loga str(exc) ou str(e) diretamente em
blocos de tratamento de exceção — prática que pode vazar credenciais
(API keys, tokens, URIs com senha) embutidas em mensagens de exceção de
bibliotecas como ccxt, aiohttp e motor.

Referência: SPEC_014 — CTRL-001 / CTRL-006 / RF-001 / DD-003.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

# Raiz de src/ relativa a este arquivo: tests/security/ -> ../../src/
_SRC_ROOT = Path(__file__).parent.parent.parent / "src"

# Padrões proibidos: str(exc), str(e), str(err), str(error) dentro de chamadas de log.
# Usamos regex para detectar o padrão mais comum.
_FORBIDDEN_LOG_PATTERN = re.compile(
    r"""(logger\.|log\.)\w+\s*\(.*?str\s*\(\s*\w+\s*\)""",
    re.DOTALL,
)

# Ocorrências explicitamente permitidas (contexto não-log).
# Chave: caminho relativo ao src/, valor: lista de linhas permitidas.
_ALLOWED_OCCURRENCES: dict[str, list[int]] = {
    # client.py: str(exc) usado apenas internamente para análise de código de erro,
    # não é logado. A variável error_message nunca chega a um logger.
    "dashboard/client.py": [240],
}


def _collect_python_files(root: Path) -> list[Path]:
    """Coleta todos os arquivos .py dentro de root recursivamente."""
    return sorted(root.rglob("*.py"))


def _is_line_allowed(relative_path: str, line_number: int) -> bool:
    """Verifica se uma ocorrência está na lista de exceções permitidas."""
    normalized = relative_path.replace("\\", "/")
    allowed_lines = _ALLOWED_OCCURRENCES.get(normalized, [])
    return line_number in allowed_lines


def _find_str_exc_in_except_blocks(source: str) -> list[tuple[int, str]]:
    """Detecta usos de str(exc)/str(e) dentro de blocos except.

    Faz parse da AST para identificar com precisão os blocos except e
    inspeciona chamadas de função em busca do padrão proibido.

    Retorna lista de (número_de_linha, trecho_de_código).
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    violations: list[tuple[int, str]] = []
    lines = source.splitlines()

    for node in ast.walk(tree):
        if not isinstance(node, ast.ExceptHandler):
            continue

        # Coleta todas as chamadas de função dentro do except handler
        for child in ast.walk(node):
            if not isinstance(child, ast.Call):
                continue

            # Verifica se é uma chamada de método (logger.warning, logger.error, etc.)
            func = child.func
            if not isinstance(func, ast.Attribute):
                continue

            # Verifica se algum argumento é str(variável)
            for arg in list(child.args) + [kw.value for kw in child.keywords]:
                if not isinstance(arg, ast.Call):
                    continue
                if not isinstance(arg.func, ast.Name):
                    continue
                if arg.func.id != "str":
                    continue
                # Encontrou str(...) em chamada de logger dentro de except
                line_no = getattr(arg, "lineno", 0)
                snippet = lines[line_no - 1].strip() if line_no > 0 else ""
                violations.append((line_no, snippet))

    return violations


def test_no_str_exc_in_log_calls() -> None:
    """Falha se qualquer módulo em src/ logar str(exc) em bloco except.

    CTRL-001 / CTRL-006 da SPEC_014: zero tolerância para str(exc) em
    chamadas de logger dentro de except handlers.
    """
    python_files = _collect_python_files(_SRC_ROOT)
    assert python_files, f"Nenhum arquivo .py encontrado em {_SRC_ROOT}"

    found_violations: list[str] = []

    for filepath in python_files:
        relative = filepath.relative_to(_SRC_ROOT.parent).as_posix()
        # Normaliza para chave de _ALLOWED_OCCURRENCES (relativo a src/)
        relative_to_src = filepath.relative_to(_SRC_ROOT).as_posix()

        try:
            source = filepath.read_text(encoding="utf-8")
        except OSError:
            continue

        violations = _find_str_exc_in_except_blocks(source)
        for line_no, snippet in violations:
            if _is_line_allowed(relative_to_src, line_no):
                continue
            found_violations.append(f"  {relative}:{line_no}  →  {snippet}")

    assert not found_violations, (
        "CTRL-001/CTRL-006 violado — str(exc) em chamada de logger dentro de except block:\n"
        + "\n".join(found_violations)
        + "\n\nSubstitua por: error_type=type(exc).__name__"
    )


def test_src_files_are_readable() -> None:
    """Verifica que todos os arquivos src/ podem ser lidos e têm sintaxe válida."""
    python_files = _collect_python_files(_SRC_ROOT)
    assert python_files, f"Nenhum arquivo .py encontrado em {_SRC_ROOT}"

    syntax_errors: list[str] = []
    for filepath in python_files:
        relative = filepath.relative_to(_SRC_ROOT.parent).as_posix()
        try:
            source = filepath.read_text(encoding="utf-8")
            ast.parse(source)
        except SyntaxError as exc:
            syntax_errors.append(f"  {relative}: {exc}")
        except OSError as exc:
            syntax_errors.append(f"  {relative}: leitura falhou — {type(exc).__name__}")

    assert not syntax_errors, "Arquivos com erro de sintaxe encontrados:\n" + "\n".join(
        syntax_errors
    )
