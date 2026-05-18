---
name: tdd
description: Conduz implementação por Test-Driven Development (Red -> Green -> Refactor) com foco em comportamento, regressão e segurança de mudança.
reference:
  - https://github.com/mattpocock/skills/tree/main/skills/engineering/tdd
tools:
  - Read
  - Bash
activation_hints:
  - "use tdd"
  - "test first"
  - "red green refactor"
  - "escrever teste antes"
  - "tdd"
---

# Skill: TDD

## Mission

Entregar mudanças com segurança incremental usando ciclo TDD, garantindo que cada
comportamento novo ou corrigido fique coberto por teste reproduzível.

## When to use

- Nova funcionalidade com comportamento claramente verificável.
- Correção de bug com cenário de reprodução objetivo.
- Refatoração que precisa de proteção contra regressão.

## Inputs mínimos

- Comportamento esperado (critério observável).
- Contexto do bug/feature (entrada, saída, efeitos colaterais).
- Suite de testes disponível e comando de execução.
- Limites de escopo para a iteração atual.

## Execution protocol

1. **Define test target**

- Especificar o menor comportamento valioso da iteração.
- Escolher seam correto (unitário, contrato ou integração).

1. **RED**

- Criar teste que falha pelo motivo certo.
- Executar teste alvo e registrar falha esperada.

1. **GREEN**

- Implementar a menor mudança possível para passar o teste.
- Executar teste alvo até passar.

1. **REFACTOR**

- Melhorar legibilidade/design sem alterar comportamento.
- Reexecutar teste alvo e validar estabilidade.

1. **Regression guard**

- Rodar bateria mínima relacionada ao domínio alterado.
- Garantir que não houve quebra colateral.

1. **Iteration loop**

- Repetir ciclo RED -> GREEN -> REFACTOR para próximo comportamento,
  mantendo passos pequenos.

1. **Closeout**

- Consolidar evidências de teste e cobertura da mudança.
- Documentar riscos remanescentes e próximos passos.

## Davi governance gates

- Se não houver comportamento verificável, voltar para refinadores.
- Mudança funcional fora de SPEC/Tasks aprovadas exige gate humano.
- Não finalizar entrega com testes novos em estado flaky.

## Output obrigatório

- Status: `done` | `partial` | `blocked`
- Comportamentos cobertos nesta rodada
- Testes criados/alterados
- Evidência RED inicial e GREEN final
- Resultado da regressão mínima
- Riscos residuais

## Quality rules

- Evitar escrever código sem teste direcionador quando aplicável.
- Testes devem falhar pelo motivo correto (não por setup quebrado).
- Mudanças devem ser pequenas, reversíveis e auditáveis.
- Refactor não pode introduzir comportamento novo não testado.
