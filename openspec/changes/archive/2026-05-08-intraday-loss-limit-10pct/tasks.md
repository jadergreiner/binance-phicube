## 1. Planejamento e contrato

- [x] 1.1 Confirmar fonte canônica de perda intraday e capital de referência diário
- [x] 1.2 Formalizar regra de bloqueio (`intraday_loss_limit_reached`) no módulo de risco

## 2. Implementação

- [x] 2.1 Implementar guarda de perda intraday com threshold fixo de 10%
- [x] 2.2 Integrar guarda ao fluxo de decisão de novas entradas sem afetar posições abertas
- [x] 2.3 Implementar reset diário da trava de entrada
- [x] 2.4 Adicionar logs/eventos estruturados para auditabilidade da decisão de bloqueio

## 3. Testes

- [x] 3.1 Adicionar testes unitários para bloquear entradas ao atingir 10% de perda
- [x] 3.2 Adicionar testes para garantir continuidade de gestão de posições abertas sob bloqueio
- [x] 3.3 Adicionar testes para reset diário do bloqueio

## 4. Validação e fechamento

- [x] 4.1 Rodar `ruff check` e testes impactados
- [x] 4.2 Atualizar status da change e evidências para `/opsx:apply`
