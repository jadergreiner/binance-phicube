---
name: sdd-spec-driven-development
description: Workflow de Spec-Driven Development (SDD) para refinar, especificar e desenvolver itens com rastreabilidade fim a fim no Binance Phicube. Use quando criar feature, corrigir bug, alterar regra de negocio, refatorar modulo critico, revisar conformidade com SPEC/PRD, ou desenvolver com apoio de IA sem ambiguidade.
argument-hint: ID da SPEC alvo e objetivo (ex: SPEC_028 + ajuste de risco no order_manager)
---

# Spec-Driven Development (SDD) - Phicube

Workflow operacional para transformar uma necessidade em implementação validada, mantendo a especificação como fonte de verdade.

## Resultado Esperado

Ao final, o item deve ter:
- Especificação clara e atualizada
- Contrato técnico verificável
- Implementação aderente
- Testes vinculados à regra
- Evidência de conformidade para merge

## Modo Obrigatório (Superpowers)

Esta skill deve sempre executar o fluxo abaixo, nesta ordem, sem pular etapas:

1. `Brainstorm`
2. `Plano`
3. `Testes`
4. `Implementação`
5. `Review`

Se alguma etapa estiver incompleta, a skill não deve sinalizar conclusão.

## Artefatos Obrigatórios por SPEC

Para toda execução da skill em uma SPEC incremental (`docs/SDD/SPEC_NNN_.../`), criar ou atualizar:

- `superpowers_brainstorm.md`
- `plan.md`
- `superpowers_test_plan.md`
- `superpowers_implementation_log.md`
- `superpowers_review.md`
- `tasks_status.json`
- `spec_status_update.md`

## Memória Operacional (Substitui Claude-Mem / Claude-Reflect)

Esta skill deve usar memória simples e local do projeto em:

- `.ai/memory/project.md`
- `.ai/memory/decisions.md`
- `.ai/memory/corrections.md`
- `.ai/memory/prompts.md`

Regras:
- Não usar estruturas paralelas de memória (ex.: Claude-Mem, Claude-Reflect)
- Ler obrigatoriamente os 4 arquivos de memória no início da execução da skill
- Atualizar obrigatoriamente os 4 arquivos ao final da execução da skill
- Atualizar somente o necessário, com entradas curtas e datadas
- Registrar fatos verificáveis, não opiniões vagas

Templates canônicos desta skill:

- `templates/superpowers_brainstorm.template.md`
- `templates/superpowers_plan.template.md`
- `templates/superpowers_test_plan.template.md`
- `templates/superpowers_implementation_log.template.md`
- `templates/superpowers_review.template.md`

## Procedimento

### 1. Brainstorm (obrigatório)

Objetivo: expandir opções de solução antes de convergir.

Ações:
- Registrar objetivo, problema e impacto esperado
- Listar ao menos 3 opções de solução (com tradeoff)
- Escolher opção recomendada com justificativa técnica
- Documentar riscos iniciais e hipóteses
- Atualizar `.ai/memory/project.md` com contexto resumido da execução

Saída obrigatória:
- `superpowers_brainstorm.md`

### 2. Plano (obrigatório)

Objetivo: converter a escolha do brainstorm em plano executável.

Ações:
- Definir escopo, fora de escopo e dependências
- Quebrar em tarefas pequenas com dono e ordem de execução
- Definir DoD objetivo
- Mapear riscos e mitigação
- Registrar decisão principal em `.ai/memory/decisions.md`

Classifique o tipo:
- Feature
- Bugfix
- Refactor
- Hotfix

Saída obrigatória:
- `plan.md`

### 3. Testes (obrigatório)

Objetivo: derivar verificação antes da implementação.

Ações:
- Mapear regra -> teste (unitário, integração, regressão)
- Definir cenários positivos, negativos e de borda
- Definir comandos de teste e evidência esperada
- Declarar gaps de cobertura e plano para fechá-los
- Registrar prompts úteis para validação em `.ai/memory/prompts.md`

Saída obrigatória:
- `superpowers_test_plan.md`

### 4. Implementação (obrigatório)

Objetivo: executar estritamente conforme SPEC e plano.

Ações:
- Atualizar primeiro a documentação aplicável (spec first)
- Implementar apenas o que está na SPEC
- Atualizar status de tarefas e decisões técnicas
- Registrar desvios e decisões no log
- Registrar correções relevantes em `.ai/memory/corrections.md`

Saídas obrigatórias:
- `superpowers_implementation_log.md`
- `tasks_status.json`

### 5. Review (obrigatório)

Objetivo: validar qualidade e conformidade antes de merge.

Ações:
- Validar aderência código <-> SPEC
- Executar testes planejados e registrar resultado
- Revisar riscos (qualidade, segurança e operação)
- Declarar aprovação, pendências ou bloqueios
- Consolidar aprendizados em `.ai/memory/project.md`

Saídas obrigatórias:
- `superpowers_review.md`
- `spec_status_update.md`

## Contexto Obrigatório

Leia e alinhe as fontes:
- `MANIFESTO.md` (princípios)
- `PRD.md` (requisitos de produto)
- `docs/SDD/SPEC.md` (fonte técnica)
- `docs/SDD/README.md` (governança SDD)
- `.ai/memory/project.md`, `.ai/memory/decisions.md`, `.ai/memory/corrections.md`, `.ai/memory/prompts.md` (memória operacional obrigatória)

Se o item afeta estratégia de trading, incluir também:
- `STRATEGY.md` (quando existir)

## Regras de Execução (Spec First)

Atualize primeiro a documentação aplicável:
- `docs/SDD/SPEC.md` para mudanças técnicas
- Documento SDD complementar, se necessário (`ARCHITECTURE.md`, `DATA_MODELS.md`, `ERROR_HANDLING.md`, `SECURITY_DESIGN.md`)

Critério de qualidade desta etapa:
- Outro engenheiro consegue implementar sem adivinhação

Regras operacionais:
- Sem decisões implícitas fora da spec
- Se surgir dúvida de regra, voltar para Brainstorm/Plano e atualizar SPEC
- IA deve receber contexto explícito da seção da spec usada

## Decisões e Ramificações

### A. Mudança de Estratégia de Trading

Se alterar lógica de sinal/entrada/saída/SL/TP:
- Consultar `@trader-senior`
- Validar consistência com método BO Williams
- Reforçar validação com skill `signal-review`

### B. Hotfix em Produção

Se urgência impedir spec prévia:
- Permitir correção imediata
- Registrar exceção
- Regularizar spec em até 24h

### C. Impacto de Segurança

Se houver mudança em segredos, acesso, Docker, env vars, dependências:
- Executar skill `security-audit`

### D. Alto Impacto em Qualidade

Se alterar fluxo de ordens, risco, persistência ou integração:
- Executar skill `qa-review`

## Definição de Pronto (DoD SDD)

- [ ] Item implementado conforme spec vigente
- [ ] Fluxo completo `Brainstorm -> Plano -> Testes -> Implementação -> Review` executado e documentado
- [ ] Testes comprovam regras e erros especificados
- [ ] PR cita seções exatas da spec alteradas
- [ ] Não há divergência entre comportamento e documentação
- [ ] `tasks_status.json` e `spec_status_update.md` atualizados para a SPEC alvo, quando aplicavel
- [ ] `.ai/memory/project.md`, `.ai/memory/decisions.md`, `.ai/memory/corrections.md`, `.ai/memory/prompts.md` lidos no início e atualizados ao final

## Prompts de Exemplo

- "Aplique a skill SDD para refinar e especificar um ajuste no Risk Manager"
- "Use a skill SDD para transformar este bug em spec + plano de implementação"
- "Execute o workflow SDD para desenvolver nova regra de entrada no Signal Engine"
- "Use a skill SDD no modo Superpowers para rodar brainstorm, plano, testes, implementação e review"
