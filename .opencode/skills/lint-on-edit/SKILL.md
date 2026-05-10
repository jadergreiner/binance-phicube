---
name: lint-on-edit
description: 'Aplica lint e formatação automática (ruff) em arquivos Python recém-criados ou editados no projeto. Use quando criar, editar ou revisar qualquer arquivo .py. Executa ruff check (lint) e ruff format (formatação) e reporta erros antes de salvar ou commitar.'
argument-hint: 'Arquivo(s) a verificar (ex: src/strategy/signal_engine.py) ou "." para todo o projeto'
---

# Lint on Edit — Phicube

Aplica lint e formatação automática em arquivos Python recém-criados ou editados, usando `ruff` conforme configurado em `pyproject.toml`.

## Quando Usar

- Após criar qualquer arquivo `.py` no projeto
- Após editar código existente
- Antes de commitar
- Ao revisar PR com foco em qualidade de código

## Ferramentas

| Ferramenta | Finalidade | Config |
|---|---|---|
| `ruff check` | Lint (E, F, I, UP) | `pyproject.toml § [tool.ruff.lint]` |
| `ruff format` | Formatação (line-length 100) | `pyproject.toml § [tool.ruff]` |

## Procedimento

### 1. Identificar o alvo

- Se o argumento for um arquivo específico: usar o caminho relativo (ex: `src/strategy/signal_engine.py`)
- Se o argumento for `.`: aplicar em todo o projeto
- Se nenhum argumento: aplicar nos arquivos modificados desde o último commit

```powershell
# Arquivos modificados desde o último commit
git diff --name-only HEAD | Where-Object { $_ -match '\.py$' }
```

### 2. Executar lint

```bash
ruff check <alvo>
```

- Se retornar erros: listar com arquivo, linha e código do erro
- Se retornar 0 erros: confirmar "lint ok"

Erros mais comuns no projeto:
- `E501`: linha maior que 100 caracteres
- `F401`: import não utilizado
- `I001`: imports fora de ordem
- `UP`: uso de sintaxe antiga (ex: `Optional[x]` em vez de `x | None`)

### 3. Corrigir automaticamente o que for seguro

```bash
ruff check --fix <alvo>
```

Correções automáticas seguras:
- Reordenar imports (`I`)
- Modernizar sintaxe (`UP`)
- Remover imports não utilizados (`F401`)

### 4. Aplicar formatação

```bash
ruff format <alvo>
```

Garante:
- Indentação consistente
- Line-length ≤ 100
- Aspas e espaçamento padronizados

### 5. Verificar resultado final

```bash
ruff check <alvo>
ruff format --check <alvo>
```

- Se ambos retornarem 0: arquivo está em conformidade
- Se ainda houver erros manuais (ex: lógica, type hints): reportar ao usuário com contexto

## Critérios de Conclusão

- [ ] `ruff check <alvo>` retorna 0 erros
- [ ] `ruff format --check <alvo>` retorna "All files already formatted" ou formatação aplicada
- [ ] Nenhum `noqa` adicionado sem justificativa explícita
