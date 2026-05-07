---
name: sdd-spec-driven-development
description: Workflow de Spec-Driven Development (SDD) para refinar, especificar e desenvolver itens com rastreabilidade fim a fim no Binance Phicube. Use quando criar feature, corrigir bug, alterar regra de negocio, refatorar modulo critico, revisar conformidade com SPEC/PRD, ou desenvolver com apoio de IA sem ambiguidade.
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

## Procedimento

### 1. Definir Escopo do Item

Registre em 3 linhas:
- Objetivo do item
- Problema que resolve
- Impacto esperado (negócio/técnico)

Classifique o tipo:
- Feature
- Bugfix
- Refactor
- Hotfix

### 2. Levantar Contexto Obrigatório

Leia e alinhe as fontes:
- `MANIFESTO.md` (princípios)
- `PRD.md` (requisitos de produto)
- `docs/SDD/SPEC.md` (fonte técnica)
- `docs/SDD/README.md` (governança SDD)

Se o item afeta estratégia de trading, incluir também:
- `STRATEGY.md` (quando existir)

### 3. Refinar Antes de Codar

Defina explicitamente:
- Regras de negócio
- Critérios de aceite
- Cenários de erro
- Limites e restrições
- Riscos (financeiros, operacionais, segurança)

Formato mínimo recomendado:
- Regra: "o sistema deve..."
- Aceite: condição objetiva e mensurável
- Erro: código/comportamento esperado

### 4. Atualizar a Especificação (Spec First)

Atualize primeiro a documentação aplicável:
- `docs/SDD/SPEC.md` para mudanças técnicas
- Documento SDD complementar, se necessário (`ARCHITECTURE.md`, `DATA_MODELS.md`, `ERROR_HANDLING.md`, `SECURITY_DESIGN.md`)

Critério de qualidade desta etapa:
- Outro engenheiro consegue implementar sem adivinhação

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

Implementação deve seguir estritamente a especificação atualizada.

Regras de execução:
- Sem decisões implícitas fora da spec
- Se surgir dúvida de regra, voltar ao passo 4
- IA deve receber contexto explícito da seção da spec usada

### 7. Validar Conformidade e Encerrar

Rodar validações e revisão:
- Testes unitários e de integração aplicáveis
- Checklist de conformidade com a spec
- Revisão de risco (quando houver impacto financeiro)

Critérios de conclusão:
- [ ] Especificação atualizada antes do código
- [ ] Código aderente ao contrato definido
- [ ] Testes passando sem regressão
- [ ] Rastreabilidade documentada: requisito -> spec -> teste -> codigo

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
- [ ] Testes comprovam regras e erros especificados
- [ ] PR cita seções exatas da spec alteradas
- [ ] Não há divergência entre comportamento e documentação
- [ ] `tasks_status.json` e `spec_status_update.md` atualizados para a SPEC alvo, quando aplicavel

## Prompts de Exemplo

- "Aplique a skill SDD para refinar e especificar um ajuste no Risk Manager"
- "Use a skill SDD para transformar este bug em spec + plano de implementação"
- "Execute o workflow SDD para desenvolver nova regra de entrada no Signal Engine"
