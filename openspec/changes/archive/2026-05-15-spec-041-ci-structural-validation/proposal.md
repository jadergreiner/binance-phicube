## Why

O CI atual valida qualidade de código e cobertura global, mas ainda não protege
integridade estrutural do repositório, como sincronia entre `.env.example` e
`Settings`, freshness de SPECs e violações arquiteturais por import indevido.
Esta mudança é necessária agora para reduzir risco de deploy quebrado,
documentação desatualizada e regressões de arquitetura em PRs.

## What Changes

- Introduzir uma esteira CI dedicada para validação estrutural em pull requests.
- Adicionar validação automática de sincronia entre campos obrigatórios de
  `src/config/settings.py` e variáveis documentadas em `.env.example`.
- Adicionar validação de freshness de SPECs para identificar artefatos stale
  com regras diferenciadas por status.
- Adicionar validação de fronteiras de camada por análise de imports em `src/`.
- Integrar verificação de segredos no diff como gate de segurança complementar.
- Definir saída de validação com erros bloqueantes e warnings não bloqueantes
  para reduzir falso positivo sem perder governança.

## Capabilities

### New Capabilities

- `ci-structural-validation`: Pipeline e regras de validação estrutural de
  configuração, documentação técnica, arquitetura de camadas e higiene de
  segurança no fluxo de PR.

### Modified Capabilities

- Nenhuma.

## Impact

- Código afetado: `.github/workflows/`, `tools/` e `tests/tools/` com novos
  validadores e testes.
- CI/CD: novo workflow acionado em PR, complementar aos gates existentes.
- Documentação operacional: atualização de diretrizes para interpretação dos
  validadores e tratamento de falhas.
- Segurança e governança: detecção antecipada de segredos no diff e drift de
  documentação/configuração.
