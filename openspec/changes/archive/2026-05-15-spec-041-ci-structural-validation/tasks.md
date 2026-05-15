## 1. Estrutura base do workflow

- [x] 1.1 Criar `.github/workflows/spec041-validation.yml` com gatilho em
      `pull_request`
- [x] 1.2 Configurar setup de Python e execução sequencial dos validadores
      estruturais
- [x] 1.3 Definir política de falha para `ERROR` e reporte para `WARNING`
      no job estrutural

## 2. Validadores de configuração e documentação

- [x] 2.1 Implementar `tools/validate_env_example.py` para comparar
      `.env.example` e `src/config/settings.py`
- [x] 2.2 Implementar validação de severidade no `validate_env_example`
      (missing obrigatório = erro, excedente = warning)
- [x] 2.3 Implementar `tools/validate_spec_freshness.py` com `--max-age`
      configurável e severidade por status da SPEC
- [x] 2.4 Padronizar saída textual dos validadores com classificação
      `ERROR`/`WARNING`

## 3. Validador de arquitetura e segurança

- [x] 3.1 Implementar `tools/validate_layers.py` com parsing AST de imports
- [x] 3.2 Definir matriz de dependências permitidas por camada e mensagens de
      violação com origem/destino
- [x] 3.3 Integrar scanner de segredos no diff do PR no workflow
      `spec041-validation`

## 4. Testes e evidências de qualidade

- [x] 4.1 Criar testes unitários para `validate_env_example.py` em
      `tests/tools/`
- [x] 4.2 Criar testes unitários para `validate_spec_freshness.py` em
      `tests/tools/`
- [x] 4.3 Criar testes unitários para `validate_layers.py` em `tests/tools/`
- [x] 4.4 Executar `pytest tests/tools/ -v` e corrigir falhas
- [x] 4.5 Executar `ruff check src/ tests/ tools/` e `ruff format src/ tests/ tools/`

## 5. Integração e fechamento operacional

- [x] 5.1 Validar execução do workflow em PR sem falso positivo no estado atual
      do repositório
- [x] 5.2 Atualizar documentação operacional com instruções dos validadores
- [x] 5.3 Executar `openspec validate --strict spec-041-ci-structural-validation`
      e confirmar change válida
