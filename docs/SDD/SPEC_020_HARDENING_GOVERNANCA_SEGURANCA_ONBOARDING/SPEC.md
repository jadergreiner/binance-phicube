# SPEC_020 — Hardening de Governança SDD, Segurança de Endpoints Sensíveis e Fechamento Operacional de Onboarding

**ID:** SPEC_020  
**Título:** Hardening de Governança SDD + Segurança de Escrita + Fechamento Operacional de Onboarding  
**Status:** Concluída  
**Data:** 2026-05-06  
**Prioridade:** Alta  
**Autores:** Time A (Refinamento) + Time B (Execução)

---

## 1. Objetivo

Consolidar o próximo pacote de entrega com foco em três frentes: (1) normalização de evidências de conclusão das SPECs recentes, (2) proteção de endpoints de escrita com controle mínimo de acesso, e (3) redução da fricção operacional do onboarding de símbolo.

---

## 2. Problema Resolvido

O estado atual apresenta inconsistência de governança (SPECs marcadas como concluídas sem trilha padronizada completa em todos os casos), risco operacional por endpoints sensíveis sem proteção explícita e dependência manual no fechamento do onboarding.

---

## 3. Escopo

### In-Scope

1. Padronizar artefatos de status para SPEC_013, SPEC_015, SPEC_016, SPEC_017, SPEC_018 e SPEC_019:
   - `tasks_status.json`
   - `spec_status_update.md`
2. Implementar proteção para endpoints de escrita sensíveis (ex.: onboarding `POST`/`DELETE` e ações equivalentes que alteram estado).
3. Consolidar fluxo operacional de onboarding para minimizar etapas manuais e explicitar o processo de ativação com segurança.
4. Garantir rastreabilidade completa `PRD -> SPEC_020 -> testes -> código`.

### Out-of-Scope

1. Redesenho completo de IAM/RBAC corporativo.
2. Replataformização do dashboard.
3. Implementação de múltiplas estratégias de trading (permanece backlog de fase posterior).

---

## 4. Requisitos Funcionais

### RF-020-01 — Governança SDD Consistente

- Toda SPEC alvo deve possuir `tasks_status.json` e `spec_status_update.md` válidos e alinhados ao estado real de implementação.

### RF-020-02 — Controle de Acesso em Endpoints Sensíveis

- Endpoints de escrita devem exigir autenticação mínima configurável por ambiente.
- Requisição sem credencial válida deve retornar erro explícito (401/403 conforme contrato definido).

### RF-020-03 — Fechamento Operacional do Onboarding

- O fluxo de onboarding deve deixar explícita e auditável a transição para operação.
- O sistema deve reduzir passos manuais ou, quando não elimináveis, padronizar instrução e validação de execução.

---

## 5. Requisitos Não Funcionais

1. Observabilidade: logs estruturados para tentativas de escrita negadas e ações autorizadas.
2. Segurança: segredo/token nunca exposto em logs.
3. Compatibilidade: comportamento legado de leitura (GET) não deve regredir.
4. Testabilidade: cobertura de cenários positivo/negativo dos controles adicionados.

---

## 6. Critérios de Aceite

- [ ] CA-020-01: SPEC_013, 015, 016, 017, 018 e 019 possuem artefatos de status padronizados e coerentes com evidências.
- [ ] CA-020-02: Endpoints sensíveis rejeitam acesso sem credencial válida com resposta e log estruturados.
- [ ] CA-020-03: Fluxo de onboarding possui fechamento operacional definido, documentado e validado por testes.
- [ ] CA-020-04: Nenhuma regressão em endpoints de leitura e funcionalidades atuais do dashboard.
- [ ] CA-020-05: Rastreabilidade documentada em `spec_status_update.md` da SPEC_020.

---

## 7. Riscos e Mitigações

| risco | impacto | mitigacao |
|---|---|---|
| Bloqueio de operações legítimas por regra de acesso restritiva | alto | Introduzir flag de ambiente, testes de contrato e rollout gradual |
| Divergência entre status documental e código real | medio | Auditoria por SPEC com checklist objetivo e evidência por arquivo/teste |
| Regressão no onboarding existente | medio | Testes de integração e validação de fluxo fim a fim |

---

## 8. Estratégia de Implementação

1. Auditar e normalizar artefatos de status das SPECs alvo.
2. Definir contrato de autenticação mínima para endpoints sensíveis.
3. Implementar middleware/dependência de proteção e testes.
4. Ajustar fluxo operacional do onboarding e documentação.
5. Executar validação final com evidências consolidadas.

---

## 9. Rastreabilidade

| Fonte | Mapeamento |
|---|---|
| PRD.md | Segurança, auditabilidade e disciplina operacional |
| docs/SDD/README.md | Semântica canônica de status e governança SDD |
| SPEC_019 | Base do fluxo de onboarding alvo de hardening |

---

## 10. Definition of Done (DoD)

- [ ] Implementação concluída conforme escopo in-scope.
- [ ] Testes de segurança e integração passando.
- [ ] `tasks.json` e `tasks_status.json` atualizados.
- [ ] `spec_status_update.md` preenchido com evidências reais.
- [ ] Atualização de índice SDD (`docs/SDD/README.md`) com status da SPEC_020.
