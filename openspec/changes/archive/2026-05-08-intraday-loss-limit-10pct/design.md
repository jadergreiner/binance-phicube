## Context

O RiskManager atual calcula tamanho de posição por risco fixo e limites de margem/alocação, mas não possui trava de perda diária agregada. Em cenário intraday adverso, o sistema pode continuar abrindo novas posições mesmo após perda material.

## Goals / Non-Goals

**Goals:**
- Impedir novas entradas quando perda intraday acumulada atingir 10%.
- Garantir rastreabilidade (motivo de bloqueio e métricas de perda).
- Permitir retomada automática no próximo dia operacional.

**Non-Goals:**
- Fechar posições automaticamente ao atingir limite.
- Alterar estratégia de sinal.
- Introduzir limite variável por símbolo nesta mudança.

## Decisions

- Decisão 1: Limiar fixo de 10% na primeira versão.
  - Racional: regra clara, auditável e de baixo atrito para adoção.
  - Alternativa: limiar configurável por símbolo.
  - Descarte: amplia escopo e complexidade de validação inicial.

- Decisão 2: Bloqueio apenas de novas entradas, sem intervenção em posições abertas.
  - Racional: reduz risco operacional sem criar side effects de execução forçada.

- Decisão 3: Reset diário por data operacional (timezone do sistema já padronizada).
  - Racional: comportamento previsível e alinhado com governança intraday.

## Risks / Trade-offs

- [Risco] Cálculo incorreto de perda acumulada por inconsistência de fonte de PnL.
  -> Mitigação: definir fonte canônica e cobrir cenários em teste.

- [Risco] Bloqueio indevido por ruído temporário.
  -> Mitigação: log detalhado do threshold, base e perda acumulada.

- [Trade-off] Limiar fixo pode ser conservador para alguns ativos.
  -> Mitigação: evoluir para parâmetro configurável em SPEC futura.

## Migration Plan

1. Adicionar contrato de guarda de perda intraday no módulo de risco.
2. Integrar verificação antes da abertura de nova ordem.
3. Incluir testes unitários e de fluxo para bloqueio e reset diário.
4. Validar observabilidade dos eventos de bloqueio.

## Open Questions

- Fonte oficial de perda intraday será PnL realizado, não realizado, ou combinado?
- Capital de referência diário será saldo no início do dia ou patrimônio dinâmico?
