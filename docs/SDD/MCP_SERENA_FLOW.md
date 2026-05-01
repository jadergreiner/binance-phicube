# Fluxo Objetivo MCP Serena — Binance Phicube

**Versão:** 1.0
**Data:** 2026-05-01
**Status:** Ativo
**Escopo:** Planejamento, execução e validação orientados por SPEC

---

## 1. Objetivo

Padronizar um fluxo único de entrega para reduzir ambiguidade e aumentar previsibilidade:

```text
SPEC -> Planner Agent -> Task Graph -> Dev Agent (com Serena) -> Validation Agent -> Commit / Review Gate
```

Este fluxo é obrigatório para features, bugfixes de médio impacto e mudanças de arquitetura.

---

## 2. Princípios de Operação

1. **Spec first:** sem SPEC aprovada, não inicia implementação.
2. **Task Graph explícito:** toda execução nasce de tarefas rastreáveis.
3. **Execução com Serena:** Dev Agent usa Serena para leitura/edição sem adivinhação.
4. **Validação independente:** Validation Agent não implementa código.
5. **Gate antes de commit:** sem aprovação de validação, não há merge.

---

## 2.1 Contrato de Uso Serena (obrigatório)

Distribuição por papel:

- **Planner Agent:** não usa Serena para edição de código; foco em decomposição e dependências.
- **Dev Agent:** uso forte de Serena para localizar símbolos, mapear impacto e editar.
- **Validation Agent:** usa Serena para diagnóstico, referências e verificação de conformidade.

Ciclo obrigatório de edição (Dev Agent):

1. Localizar símbolo/alvo.
2. Mapear referências e implementações impactadas.
3. Editar com rastreabilidade task -> alteração.
4. Rodar diagnósticos por símbolo/arquivo.
5. Validar impacto antes de enviar ao gate.

Contrato de ferramentas:

```yaml
serena_usage:
  search:
    tool: find_file
    rule: "não editar sem localizar alvo e contexto"
  navigation:
    tools:
      - jet_brains_find_referencing_symbols
      - jet_brains_find_implementations
    rule: "mapear impacto antes de alterar contrato público"
  diagnostics:
    tool: get_diagnostics_for_symbol
    rule: "executar após qualquer modificação relevante"
```

---

## 3. Pipeline Operacional

### Etapa A — SPEC (entrada)

**Entrada mínima obrigatória:**

- SPEC em `docs/SDD/SPEC_NNN_*/SPEC.md`
- Objetivo, escopo, non-goals e critérios de aceitação
- Contratos técnicos e regras de erro

**Saída da etapa:**

- SPEC com status **Aprovada**

---

### Etapa B — Planner Agent

**Responsabilidade:** transformar SPEC aprovada em plano executável.

**Entrega obrigatória:**

- Task Graph com dependências e prioridade
- Critérios de pronto por task
- Riscos e mitigação por task
- Mapeamento task -> arquivos/módulos esperados

**Formato mínimo do Task Graph:**

```text
TG-001 [P0] Definir contrato de entrada/saída
  deps: -
  done_when: contratos validados com SPEC

TG-002 [P0] Implementar serviço de leitura
  deps: TG-001
  done_when: testes unitários verdes

TG-003 [P1] Expor endpoint/canal de atualização
  deps: TG-002
  done_when: integração validada em Testnet
```

---

### Etapa C — Dev Agent (com Serena)

**Responsabilidade:** implementar estritamente o Task Graph.

**Regras:**

- Não alterar escopo sem retorno ao Planner Agent.
- Cada tarefa executada deve citar o ID da task (ex.: TG-002).
- Toda mudança deve manter rastreabilidade para a SPEC.

**Saída da etapa:**

- Implementação concluída
- Testes locais executados
- Evidências técnicas por task

---

### Etapa D — Validation Agent

**Responsabilidade:** validar conformidade sem participar da implementação.

**Checklist obrigatório:**

- Conformidade SPEC -> código
- Cobertura dos critérios de aceitação
- Cenários de erro e casos de borda
- Qualidade e estabilidade dos testes
- Risco operacional e segurança (quando aplicável)

**Saída da etapa:**

- Parecer: **APROVADO** ou **REPROVADO**
- Lista de não conformidades (quando houver)

---

### Etapa E — Commit / Review Gate

**Condição de entrada no gate:**

- Validation Agent com parecer **APROVADO**
- Evidências anexadas

**Ações do gate:**

1. Revisão final de escopo (sem creep)
2. Commit em Conventional Commits
3. Push e PR com rastreabilidade SPEC -> Task Graph -> testes

**Critério de bloqueio:**

- Qualquer não conformidade aberta bloqueia commit/merge

---

## 4. RACI do Fluxo

| Etapa | Responsável (R) | Aprovador (A) | Consultados (C) | Informados (I) |
|---|---|---|---|---|
| SPEC | Time A | Product Owner | Risk Manager, Quant | Time B |
| Planner | Planner Agent | Product Owner | Backend, Quant | Validation |
| Execução | Dev Agent | Backend Sênior | Quant, AppSec, QA | Product Owner |
| Validação | Validation Agent | QA/Quality Gate | AppSec, Quant | Product Owner |
| Commit/Gate | Time B | Product Owner | Validation Agent | Time A |

---

## 5. Definition of Ready (DoR)

Item só entra em execução quando:

- SPEC aprovada e versionada
- Task Graph completo e priorizado
- Dependências técnicas identificadas
- Critérios de validação definidos

---

## 6. Definition of Done (DoD)

Item só é concluído quando:

- Tasks do Task Graph concluídas
- Validation Agent aprovou
- Commit e review gate aprovados
- PR contém rastreabilidade completa

---

## 7. Prompt Base Recomendado

```text
Executar fluxo MCP Serena para a SPEC_NNN:
1) Planner Agent gera Task Graph com prioridade e dependências
2) Dev Agent implementa por ID de task
3) Validation Agent valida conformidade e testes
4) Só então liberar Commit / Review Gate
```

---

## Histórico

- **2026-05-01:** Criação do fluxo objetivo MCP Serena.
