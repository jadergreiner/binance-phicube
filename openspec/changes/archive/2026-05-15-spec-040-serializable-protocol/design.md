## Context

O projeto possui múltiplas dataclasses com `to_dict()` manual, repetindo a
mesma lógica em módulos de estratégia, risco, execução e backtest. Esse padrão
duplica código e facilita regressões quando campos novos são adicionados sem
atualizar serialização, com impacto direto em persistência MongoDB e fluxos
internos de observabilidade.

Restrições relevantes:

- Compatibilidade de payload é mandatória para não quebrar consumidores
  existentes.
- Segurança exige impedir exposição de segredos em serialização padronizada.
- Mudança é transversal e precisa de rollout incremental com validação de
  paridade.

Stakeholders principais:

- Engenharia de bot/runtime (estabilidade operacional)
- Engenharia de API/dashboard (consumo de payload)
- QA/observabilidade (regressão e rastreabilidade)

## Goals / Non-Goals

**Goals:**

- Definir contrato único de serialização (`Serializable`) para uso tipado.
- Padronizar geração de `to_dict()` em dataclasses com mecanismo reutilizável.
- Garantir compatibilidade funcional do formato serializado pós-migração.
- Incluir política explícita para campos sensíveis no fluxo de serialização.

**Non-Goals:**

- Introduzir formatos binários ou schema registry.
- Resolver versionamento de schema entre serviços.
- Reestruturar consumidores externos além da paridade de payload atual.

## Decisions

### 1) Centralizar serialização em `src/common/serialization.py`

Decisão: criar módulo comum com protocolo `Serializable` e decorador de geração
automática.

Racional:

- Evita duplicação e facilita adoção gradual por módulo.
- Mantém contrato explícito e verificável por tipagem.

Alternativas consideradas:

- Manter `to_dict()` manual por dataclass: rejeitada por alto custo de
  manutenção e risco de omissão.
- Utilizar utilitários genéricos dispersos por módulo: rejeitada por baixa
  coerência arquitetural.

### 2) Estratégia de não sobrescrever `to_dict()` existente

Decisão: se a dataclass já possuir `to_dict()` manual, o mecanismo automático
não substitui implementação existente.

Racional:

- Preserva compatibilidade durante migração faseada.
- Permite refatorar por lotes com validação de paridade por classe.

Alternativas consideradas:

- Forçar sobrescrita imediata em todas as classes: rejeitada por alto risco de
  regressão operacional.

### 3) Serialização recursiva para objetos aninhados e listas

Decisão: o `to_dict()` gerado deve converter campos que implementam `to_dict()`
e listas de objetos serializáveis, preservando ordem.

Racional:

- Atende estruturas de domínio já usadas no projeto.
- Reduz necessidade de mapeamento manual para cenários compostos.

Alternativas consideradas:

- Suportar apenas tipos primitivos: rejeitada por cobertura insuficiente.

### 4) Política de segurança para campos sensíveis

Decisão: campos classificados como segredo devem ser omitidos ou mascarados no
resultado serializado.

Racional:

- Alinha com diretriz de não vazamento de segredos em logs/payloads.
- Reduz risco operacional e de compliance.

Alternativas consideradas:

- Não aplicar filtro no núcleo e delegar para consumidores: rejeitada por risco
  de uso incorreto e falta de defesa em profundidade.

## Risks / Trade-offs

- [Mudança acidental de formato de payload] → Mitigação: testes de paridade
  comparando saída antes/depois para dataclasses refatoradas.
- [Adoção parcial gera comportamento misto] → Mitigação: estratégia incremental
  explícita com classes alvo definidas por etapa.
- [Serialização recursiva em estruturas cíclicas] → Mitigação: detecção de
  ciclo e fallback controlado para evitar recursão infinita.
- [Falso positivo/negativo na classificação de segredo] → Mitigação: política
  documentada com casos de teste dedicados e revisão em PR.

## Migration Plan

1. Implementar módulo comum de serialização (`Serializable` + gerador
   automático).
2. Cobrir com testes unitários do módulo (geração, preservação, recursão,
   listas, erro em uso inválido).
3. Migrar dataclasses prioritárias em lotes pequenos (ex.: Signal,
   SignalEvaluation, PositionSize, Trade).
4. Executar testes de paridade de `to_dict()` para cada lote antes de avançar.
5. Habilitar validação no pipeline de qualidade para impedir regressão de
   serialização.

Rollback:

- Reverter lote específico de dataclasses para `to_dict()` manual mantendo
  módulo comum intacto.
- Se necessário, remover decorador das classes afetadas sem alterar contrato
  externo de consumidores.

## Open Questions

- Quais critérios finais definem um campo como sensível para omissão ou máscara
  (nome, tipo, metadado de campo, combinação)?
- O módulo de serialização deve oferecer estratégia configurável de tratamento
  para tipos não serializáveis (erro, repr, null)?
- Quais dataclasses de backtest entram na primeira onda versus fase posterior?
