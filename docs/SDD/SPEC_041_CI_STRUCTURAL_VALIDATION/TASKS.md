## SPEC_041 - Tasks

## 1. Estrutura base do workflow

- [x] 1.1 Criar `.github/workflows/spec041-validation.yml` com gatilho em PR
- [x] 1.2 Configurar setup de Python e execução sequencial dos validadores
- [x] 1.3 Definir política de falha para `ERROR` e reporte para `WARNING`

## 2. Validadores de configuração e documentação

- [x] 2.1 Implementar `tools/validate_env_example.py`
- [x] 2.2 Implementar severidade (`missing` obrigatório = erro, `extra` = warning)
- [x] 2.3 Implementar `tools/validate_spec_freshness.py` com `--max-age`
- [x] 2.4 Padronizar saída textual com `ERROR`/`WARNING`

## 3. Arquitetura e segurança

- [x] 3.1 Implementar `tools/validate_layers.py` com AST
- [x] 3.2 Definir matriz de imports permitidos por camada
- [x] 3.3 Integrar scanner de segredos no workflow

## 4. Testes e qualidade

- [x] 4.1 Criar `tests/tools/test_validate_env_example.py`
- [x] 4.2 Criar `tests/tools/test_validate_spec_freshness.py`
- [x] 4.3 Criar `tests/tools/test_validate_layers.py`
- [x] 4.4 Executar `pytest` do escopo e corrigir falhas
- [x] 4.5 Executar `ruff check` no escopo alterado

## 5. Fechamento operacional

- [x] 5.1 Validar baseline local dos validadores sem erro bloqueante
- [x] 5.2 Atualizar `docs/OPERATIONS.md` com instruções dos validadores
- [x] 5.3 Validar artefatos OpenSpec da SPEC_041 em modo estrito
