# SPEC_041 — Pipeline CI de Validação Estrutural

**ID:** SPEC_041
**Status:** Rascunho
**Data:** 2026-05-11
**Versão:** 1.0
**Dependências:** Nenhuma
**Skill de validação:** `sdd-spec-driven-development`, `security-audit`

---

## 1. Título e Resumo

### 1.1 Nome da Funcionalidade

Workflow CI de validação estrutural do repositório

### 1.2 Resumo

**O que é:** Uma esteira CI (GitHub Actions) que valida a integridade estrutural do repositório em cada PR: sincronia entre `.env.example` e `Settings`, detecção de SPECs stale, verificação de cobertura por módulo, e gates de qualidade complementares aos existentes (`spec023-validation`, `spec021-validation`).

**Por que estamos fazendo:** Atualmente o CI cobre qualidade de código (lint + testes + coverage ≥ 80%), mas não valida: (a) se o `.env.example` reflete os campos reais de `settings.py`, (b) se SPECs foram marcadas como obsoletas após implementação, (c) se há arquivos temporários ou segredos vazados.

**Valor de negócio:** Previne `.env` quebrado em deploy, mantém documentação técnica viva, detecta vazamento de secrets antes do push.

**Conexão com PRD/SPEC:** Complementar às workflows `spec023-validation.yml` e `spec021-validation.yml`.

---

## 2. Objetivos e Escopo

### 2.1 Objetivos

- [ ] Validar `.env.example` vs `Settings` do Pydantic — todo campo obrigatório tem exemplo, todo campo no example existe no Settings
- [ ] Detectar SPECs com `status_update.md` desatualizado (> 90 dias sem alteração)
- [ ] Verificar ausência de arquivos `.env`, `*.key`, `credentials.*` no staged diff
- [ ] Reportar cobertura de testes por módulo (gate mínimo por módulo, não apenas global)
- [ ] Validar que imports em `src/` não cruzam camadas proibidas (ex: `src/strategy` importar `src/api`)

### 2.2 Fora do Escopo

- **Não inclui:** Execução de testes end-to-end ou backtest
- **Não inclui:** Deploy automático
- **Não inclui:** Validação de performance (benchmarks)

---

## 3. Referências

| Documento | Seção | Relevância |
|---|---|---|
| `.github/workflows/spec023-validation.yml` | — | Workflow existente de cobertura |
| `.github/workflows/spec021-validation.yml` | — | Workflow existente de quality gate |
| `src/config/settings.py` | — | Fonte da verdade para validação de .env |
| `docs/SDD/SPEC_TEMPLATE.md` | — | Template com campos de status/data |

---

## 4. Histórias de Usuário e Requisitos

### US-041-01: Validação `.env.example` vs `Settings`

> Como **devops**, quero **validação automática em PR de que `.env.example` está sincronizado com `Settings` do Pydantic** para **nunca fazer deploy com variável obrigatória faltando**.

**Critérios de Aceitação:**

```text
DADO   um PR que adiciona um campo obrigatório em settings.py
QUANDO o CI executa spec041-validation
ENTÃO  falha se `.env.example` não tem o campo
```

```text
DADO   um PR que remove um campo de settings.py
QUANDO o CI executa
ENTÃO  warning se `.env.example` ainda tem o campo (não blocking)
```

- [ ] AC-01: Script `tools/validate_env_example.py` compara campos de Settings com `.env.example`
- [ ] AC-02: CI step `validate-env` roda `python tools/validate_env_example.py`

### US-041-02: Detecção de SPECs stale

> Como **engenheiro de documentação**, quero **detecção de SPECs sem atualização há mais de 90 dias** para **manter o SPEC index confiável**.

- [ ] AC-01: Script varre `docs/SDD/SPEC_*/SPEC.md` e verifica `Data:` vs hoje
- [ ] AC-02: SPECs com status "Concluída" e data > 90 dias geram WARNING
- [ ] AC-03: SPECs com status "Rascunho" e data > 90 dias geram ERROR

### US-041-03: Layer validation (imports)

> Como **arquiteto**, quero **validação automática de que camadas não violam a arquitetura** para **impedir acoplamentos indevidos**.

**Regras de camada:**

| Camada | Pode importar |
|---|---|
| `src/strategy` | `src/monitoring` |
| `src/trading` | `src/strategy`, `src/exchange`, `src/notifications` |
| `src/api` | `src/storage`, `src/strategy` (modelos) |
| `src/exchange` | `src/monitoring` |
| `src/storage` | `src/monitoring` |
| `src/notifications` | `src/monitoring` |
| `src/backtest` | `src/strategy`, `src/trading`, `src/exchange` |

- [ ] AC-01: Script `tools/validate_layers.py` varre imports e verifica regras
- [ ] AC-02: Violação de camada → CI failure

---

## 5. Design e Arquitetura

### 5.1 Workflow `spec041-validation.yml`

```yaml
name: spec041-validation
on: [pull_request]

jobs:
  structural-validation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Validate .env.example vs Settings
        run: python tools/validate_env_example.py

      - name: Detect stale SPECs
        run: python tools/validate_spec_freshness.py --max-age=90

      - name: Validate layer imports
        run: python tools/validate_layers.py

      - name: Scan for secrets in diff
        uses: trufflesecurity/trufflehog@v3
        with:
          mode: diff
```

### 5.2 Scripts de Validação

**`tools/validate_env_example.py`:**

```python
"""Valida que .env.example contém todos os campos obrigatórios de Settings."""
from src.config.settings import Settings

# Instancia Settings com valores dummy para verificar campos
# Compara campos do model.json() com chaves no .env.example
...

exit(0 if all_found else 1)
```

**`tools/validate_layers.py`:**

```python
"""Valida regras de importação entre camadas usando AST."""
import ast
from pathlib import Path

LAYER_RULES = {
    "src/strategy": {"src/monitoring"},
    "src/trading": {"src/strategy", "src/exchange", "src/notifications", "src/monitoring"},
    ...
}

# Para cada .py em src/, parse AST, extrai imports, verifica contra regras
...
```

---

## 6. Regras de Negócio e Restrições

### 6.1 Invariantes

| ID | Invariante | Violação → Ação |
|---|---|---|
| INV-041-01 | Settings.None fields SEMPRE têm exemplo em `.env.example` | CI failure |
| INV-041-02 | Nenhum `.env` ou `*.key` no staged diff | CI failure + notificação |
| INV-041-03 | Layer violations bloqueiam merge | CI failure |

---

## 7. Implementação

### 7.1 Arquivos a Criar

| Arquivo | Descrição |
|---|---|
| `.github/workflows/spec041-validation.yml` | Workflow principal |
| `tools/validate_env_example.py` | Valida sincronia .env ↔ Settings |
| `tools/validate_spec_freshness.py` | Detecta SPECs desatualizadas |
| `tools/validate_layers.py` | Valida camadas de importação |
| `tests/tools/test_validate_env_example.py` | Testes dos validadores |

### 7.2 Evidências Requeridas na PR

- [ ] Workflow executa em PR sem falsos positivos no código atual
- [ ] Testes unitários para cada validador
- [ ] Documentação em `docs/OPERATIONS.md` sobre os validadores

---

## 8. Riscos e Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| Falso positivo em .env (campo opcional não documentado) | Médio | Whitelist de campos que não precisam de example |
| Layer validation muito restritiva | Médio | Regras configuráveis via dicionário, não hardcoded |
| SPEC freshness depende de data manual | Baixo | CI sugere atualização automática da data |

---

## 9. Definição de Pronto (DoD)

- [ ] Workflow `spec041-validation.yml` criado e rodando em PRs
- [ ] 3 scripts validador: .env, SPEC freshness, layers
- [ ] Validação de segredos no diff via trufflehog
- [ ] Testes unitários para cada validador
- [ ] Cobertura ≥ 80% dos scripts de validação

---

## Histórico

- **2026-05-11:** Criação da SPEC_041.
