---
name: migrate-to-shoehorn
description: Planeja e executa migração incremental para shoehorn com preservação de comportamento, rollback explícito e validação por etapas.
reference:
  - https://github.com/mattpocock/skills/tree/main/skills/misc/migrate-to-shoehorn
tools:
  - Read
  - Bash
activation_hints:
  - "use migrate-to-shoehorn"
  - "migrar para shoehorn"
  - "shoehorn migration"
  - "migração incremental"
  - "adotar shoehorn"
---

# Skill: Migrate To Shoehorn

## Mission

Conduzir migração para shoehorn de forma incremental, segura e rastreável,
minimizando regressões e garantindo reversibilidade.

## When to use

- Projeto vai adotar shoehorn como novo padrão de execução/estrutura.
- Migração afeta múltiplos módulos e precisa de etapas controladas.
- Existe risco operacional alto para migração em big bang.

## Inputs mínimos

- Estado atual do projeto (fluxos, entrypoints, contratos).
- Escopo da migração (o que entra/agora e o que fica para depois).
- Critérios de sucesso e não-regressão.
- Janela de rollout e estratégia de rollback.

## Execution protocol

1. **Migration baseline**

- Mapear arquitetura e comportamento atual relevante.
- Registrar contratos que não podem quebrar durante migração.

1. **Target mapping**

- Definir como shoehorn será adotado no projeto.
- Especificar mapeamento atual -> alvo por componente.

1. **Incremental slicing**

- Quebrar migração em lotes pequenos e independentes.
- Para cada lote, definir:
  - objetivo
  - impacto
  - testes obrigatórios
  - rollback

1. **Compatibility bridge**

- Criar camada temporária de compatibilidade quando necessário.
- Permitir convivência controlada entre estado antigo e novo.

1. **Validation per slice**

- Executar validação por lote:
  - contrato
  - integração
  - smoke operacional
- Bloquear avanço se algum gate falhar.

1. **Human migration gate**

- Submeter resultado de cada lote ao humano quando impacto for alto.
- Não avançar lote crítico sem aprovação formal.

1. **Cutover and cleanup**

- Concluir transição para estado alvo.
- Remover ponte de compatibilidade e código legado não usado.

1. **Closeout**

- Consolidar evidências de migração e riscos residuais.
- Documentar operação final e próximos passos.

## Davi governance gates

- Migração que altera regras RN/RA/RG deve voltar aos refinadores.
- Sem plano de rollback explícito, lote não inicia.
- Mudança irreversível requer aprovação humana formal.

## Output obrigatório

- Status: `ready` | `in-progress` | `blocked` | `completed`
- Baseline e estado-alvo
- Lotes de migração e dependências
- Estratégia de compatibilidade
- Evidências de validação por lote
- Rollback definido/executado (se aplicável)
- Próximo passo recomendado

## Quality rules

- Evitar migração big bang sem justificativa excepcional.
- Cada lote deve ser pequeno, testável e reversível.
- Não encerrar migração com ponte temporária sem plano de remoção.
- Toda decisão crítica deve ficar auditável.
