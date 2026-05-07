---
name: sdd-spec-driven-development
description: Workflow replicado de .claude/commands/sdd-spec-driven-development.md para 'Spec-Driven Development (SDD) — Phicube'. Use quando precisar executar esse procedimento no projeto Binance Phicube.
---

# Spec-Driven Development (SDD) — Phicube

Workflow operacional para transformar uma necessidade em implementação validada, mantendo a especificação como fonte de verdade.

**Argumento:** item a tratar (ex: `"ajuste no signal_engine"`, `"novo endpoint"`, `"bug de ordem sem SL"`)

## Quando Usar

- Refinar uma demanda nova (feature, bug, melhoria)
- Alterar regra de negócio ou estratégia
- Especificar contrato técnico antes de implementar
- Implementar item com apoio de IA sem perder aderência
- Revisar PR com foco em conformidade com spec

## Procedimento

### 1. Definir Escopo do Item

Registre em 3 linhas:
- Objetivo do item
- Problema que resolve
- Impacto esperado (negócio/técnico)

Classifique o tipo: Feature | Bugfix | Refactor | Hotfix

### 2. Levantar Contexto Obrigatório

Leia e alinhe as fontes:
- `MANIFESTO.md` (princípios)
- `PRD.md` (requisitos de produto)
- `docs/SDD/SPEC.md` (fonte técnica)
- `docs/SDD/README.md` (governança SDD)

Se o item afeta estratégia de trading, incluir também `STRATEGY.md` (quando existir).

### 3. Refinar Antes de Codar

Defina explicitamente:
- Regras de negócio
- Critérios de aceite
- Cenários de erro
- Limites e restrições
- Riscos (financeiros, operacionais, segurança)

Formato mínimo:
- Regra: "o sistema deve..."
- Aceite: condição objetiva e mensurável
- Erro: código/comportamento esperado

### 4. Atualizar a Especificação (Spec First)

Atualize primeiro a documentação aplicável:
- `docs/SDD/SPEC.md` para mudanças técnicas
- Documento SDD complementar, se necessário

Critério de qualidade: outro engenheiro consegue implementar sem adivinhação.

### 5. Derivar Contratos e Testes da Spec

Para cada regra criada/alterada, derivar:
- Contrato de entrada/saída
- Validações
- Cenários positivos
- Cenários negativos
- Casos de borda

Checklist:
- [ ] Cada regra tem pelo menos 1 teste associado
- [ ] Cenários críticos de erro estão cobertos
- [ ] Existe rastreabilidade regra -> teste

### 6. Implementar Guiado pela Spec

- Sem decisões implícitas fora da spec
- Se surgir dúvida de regra, voltar ao passo 4
- Contexto explícito da seção da spec deve guiar a implementação

### 7. Validar Conformidade e Encerrar

- [ ] Especificação atualizada antes do código
- [ ] Código aderente ao contrato definido
- [ ] Testes passando sem regressão
- [ ] Rastreabilidade documentada: requisito -> spec -> teste -> código

## Decisões e Ramificações

### A. Mudança de Estratégia de Trading

Se alterar lógica de sinal/entrada/saída/SL/TP:
- Consultar agente `trader-senior`
- Validar consistência com método BO Williams
- Executar `/signal-review`

### B. Hotfix em Produção

Se urgência impedir spec prévia:
- Permitir correção imediata
- Registrar exceção
- Regularizar spec em até 24h

### C. Impacto de Segurança

Se houver mudança em segredos, acesso, Docker, env vars, dependências:
- Executar `/security-audit`

### D. Alto Impacto em Qualidade

Se alterar fluxo de ordens, risco, persistência ou integração:
- Executar `/qa-review`

## Definição de Pronto (DoD SDD)

- [ ] Item implementado conforme spec vigente
- [ ] Testes comprovam regras e erros especificados
- [ ] PR cita seções exatas da spec alteradas
- [ ] Não há divergência entre comportamento e documentação

