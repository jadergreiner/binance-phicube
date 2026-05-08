# SDD — Software Design Document — Binance Phicube

**Versão:** 1.0
**Data:** 2026-05-01
**Status:** Ativo
**Proprietário:** Team Backend + Team Quant

---

## 📖 O que é este documento?

Este é o **Software Design Document (SDD)** — especificação técnica executável do Binance Phicube. Enquanto o **PRD.md** responde *o que o usuário precisa*, este documento responde **como os engenheiros o constroem**.

**Não é:**

- ❌ Um guia de instalação (veja README.md raiz)
- ❌ Uma teoria de trading (veja STRATEGY.md quando criado)
- ❌ Um manual operacional (veja docs/OPERATIONS.md)

**É:**

- ✅ Especificação técnica de arquitetura
- ✅ Design de componentes, interfaces, fluxos
- ✅ Padrões de código, erros, logging
- ✅ Decisões tecnológicas e justificativas
- ✅ **Source of truth para implementação**

---

## 🗺️ Navegação

### Documentos Raiz (em ordem de leitura)

1. **[SPEC.md](SPEC.md)** — Especificação técnica completa (⭐ comece aqui)
   - Arquitetura geral
   - Componentes: Signal Engine, Risk Manager, Order Manager, Storage, Logger, Exchange Integration
   - Interfaces e contratos
   - Fluxos de dados e sequências
   - Padrões de design

2. **[SPEC_TEMPLATE.md](SPEC_TEMPLATE.md)** — Template para novas SPECs incrementais
   - Use ao criar SPEC_002, SPEC_003...
   - Copie para `SPEC_NNN_TITULO/SPEC.md` e preencha

3. **[MCP_SERENA_FLOW.md](MCP_SERENA_FLOW.md)** — Fluxo objetivo de entrega com agentes
    - Pipeline oficial: SPEC -> Planner Agent -> Task Graph -> Dev Agent (Serena) -> Validation Agent -> Commit/Review Gate
    - Definições de entrada/saída por etapa e critérios de gate

4. **Superpowers Workflow (SDD Skill)** — Fluxo mandatório da skill `sdd-spec-driven-development`
   - Ordem fixa: Brainstorm -> Plano -> Testes -> Implementação -> Review
   - Artefatos por SPEC: `superpowers_brainstorm.md`, `plan.md`, `superpowers_test_plan.md`, `superpowers_implementation_log.md`, `superpowers_review.md`
   - Memória operacional simplificada: `.ai/memory/project.md`, `.ai/memory/decisions.md`, `.ai/memory/corrections.md`, `.ai/memory/prompts.md`

5. **ARCHITECTURE.md** *(em breve)* — Diagrama de arquitetura profundo

6. **DATA_MODELS.md** *(em breve)* — Esquema de dados

7. **ERROR_HANDLING.md** *(em breve)* — Estratégia de falhas

8. **SECURITY_DESIGN.md** *(em breve)* — Design de segurança

### SPECs Incrementais

Cada SPEC incremental vive em seu próprio diretório:

| Diretório | ID | Título | Status |
|---|---|---|---|
| [SPEC_001_PAINEL_POSICOES_TEMPO_REAL/](SPEC_001_PAINEL_POSICOES_TEMPO_REAL/SPEC.md) | SPEC_001 | Painel de Posições em Tempo Real (Somente Leitura) | Concluída |
| [SPEC_002_FRONTEND_CONSULTA_POSICOES/](SPEC_002_FRONTEND_CONSULTA_POSICOES/SPEC.md) | SPEC_002 | Frontend de Consulta de Posições | Concluída |
| [SPEC_003_INCLUSAO_CALCULOS_MARGEM_POSICOES/](SPEC_003_INCLUSAO_CALCULOS_MARGEM_POSICOES/SPEC.md) | SPEC_003 | Inclusão de Cálculos de Margem e ROI Ajustado | Concluída |
| [SPEC_004_NOTIFICACOES_TELEGRAM_OPERACIONAIS/](SPEC_004_NOTIFICACOES_TELEGRAM_OPERACIONAIS/SPEC.md) | SPEC_004 | Notificações Operacionais via Telegram | Concluída |
| [SPEC_005_ANALISE_BIAS_POSICOES_ABERTAS/](SPEC_005_ANALISE_BIAS_POSICOES_ABERTAS/SPEC.md) | SPEC_005 | Análise de Bias de Mercado e Oportunidades de Posições Abertas | Concluída |
| [SPEC_006_RELATORIO_PERFORMANCE_TRADES/](SPEC_006_RELATORIO_PERFORMANCE_TRADES/SPEC.md) | SPEC_006 | Relatório de Performance de Trades | Concluída |
| [SPEC_007_RESILIENCIA_CONTINUIDADE_OPERACIONAL/](SPEC_007_RESILIENCIA_CONTINUIDADE_OPERACIONAL/SPEC.md) | SPEC_007 | Resiliência e Continuidade Operacional | Concluída |
| [SPEC_008_RELATORIO_PERIODICO_TELEGRAM/](SPEC_008_RELATORIO_PERIODICO_TELEGRAM/SPEC.md) | SPEC_008 | Relatório Periódico de Performance via Telegram | Concluída |
| [SPEC_009_ANALISE_PERFORMANCE_SIMBOLO_TIMEFRAME/](SPEC_009_ANALISE_PERFORMANCE_SIMBOLO_TIMEFRAME/SPEC.md) | SPEC_009 | Análise de Performance por Símbolo e Timeframe | Concluída |
| [SPEC_010_DASHBOARD_PERFORMANCE/](SPEC_010_DASHBOARD_PERFORMANCE/SPEC.md) | SPEC_010 | Dashboard de Performance em Tempo Real | Concluída |
| [SPEC_011_MOTOR_BACKTESTING/](SPEC_011_MOTOR_BACKTESTING/SPEC.md) | SPEC_011 | Motor de Backtesting | Concluída |
| [SPEC_012_MONITORAMENTO_ORDENS_POSICOES_ABERTAS/](SPEC_012_MONITORAMENTO_ORDENS_POSICOES_ABERTAS/SPEC.md) | SPEC_012 | Monitoramento Ativo de Ordens e Posições Abertas | Concluída |
| [SPEC_013_VALIDACAO_SIGNAL_ENGINE/](SPEC_013_VALIDACAO_SIGNAL_ENGINE/SPEC.md) | SPEC_013 | Validação do Signal Engine — Curadoria, Corpus e Conformidade com o Método Phicube | Concluída |
| [SPEC_014_SECURITY_DESIGN/](SPEC_014_SECURITY_DESIGN/SPEC.md) | SPEC_014 | Security Design — Gestão de Segredos, Superfícies de Ataque e Hardening Operacional | Concluída |
| [SPEC_015_SL_ORFAO_INTERVENCAO_ASSISTIDA/](SPEC_015_SL_ORFAO_INTERVENCAO_ASSISTIDA/SPEC.md) | SPEC_015 | Monitoramento de SL Órfão — Loop de Alertas, Auditabilidade e Guia de Intervenção | Concluída |
| [SPEC_016_VISIBILIDADE_OPERACIONAL_DASHBOARD/](SPEC_016_VISIBILIDADE_OPERACIONAL_DASHBOARD/SPEC.md) | SPEC_016 | Visibilidade Operacional Completa no Dashboard | Concluída |
| [SPEC_017_SAUDE_BOT_HEARTBEAT_HEALTHCHECK/](SPEC_017_SAUDE_BOT_HEARTBEAT_HEALTHCHECK/SPEC.md) | SPEC_017 | Saúde do Bot: Heartbeat no MongoDB e Healthcheck HTTP | Concluída |
| [SPEC_018_EXPANSAO_PARES_COMMODITIES/](SPEC_018_EXPANSAO_PARES_COMMODITIES/SPEC.md) | SPEC_018 | Expansão de Pares: Commodities (XPTUSDT e COPPERUSDT) | Concluída |
| [SPEC_019_ONBOARDING_SIMBOLO/](SPEC_019_ONBOARDING_SIMBOLO/SPEC.md) | SPEC_019 | Onboarding de Símbolo — Wizard de Inclusão, Backtest e Aprovação para Produção | Concluída |
| [SPEC_020_HARDENING_GOVERNANCA_SEGURANCA_ONBOARDING/](SPEC_020_HARDENING_GOVERNANCA_SEGURANCA_ONBOARDING/SPEC.md) | SPEC_020 | Hardening de Governança SDD, Segurança de Endpoints Sensíveis e Fechamento Operacional de Onboarding | Concluída |
| [SPEC_021_VALIDACAO_OPERACIONAL_RESILIENCIA/](SPEC_021_VALIDACAO_OPERACIONAL_RESILIENCIA/SPEC.md) | SPEC_021 | Validação Operacional e Resiliência de Produção | Em Execução |
| [SPEC_022_CONVERGENCIA_PRD_SDD_CODIGO/](SPEC_022_CONVERGENCIA_PRD_SDD_CODIGO/SPEC.md) | SPEC_022 | Convergencia PRD-SDD-Codigo para Regras Criticas de Risco e Escalabilidade | Concluída |
| [SPEC_023_FECHAMENTO_GAPS_PRD_MVP_OKR/](SPEC_023_FECHAMENTO_GAPS_PRD_MVP_OKR/SPEC.md) | SPEC_023 | Fechamento de Gaps do PRD (MVP + OKR Atuais) | Em Execução |
| [SPEC_024_GESTAO_PARES_DASHBOARD/](SPEC_024_GESTAO_PARES_DASHBOARD/SPEC.md) | SPEC_024 | Gestão de Pares no Dashboard (Sessão Inferior) | Concluída |
| [SPEC_025_SINAIS_DASHBOARD_DIAGNOSTICO_EXECUCAO/](SPEC_025_SINAIS_DASHBOARD_DIAGNOSTICO_EXECUCAO/SPEC.md) | SPEC_025 | Sinais no Dashboard + Diagnóstico de Não Execução | Concluída |
| [SPEC_026_NORMALIZACAO_HORARIO_BR_PAINEL_API/](SPEC_026_NORMALIZACAO_HORARIO_BR_PAINEL_API/SPEC.md) | SPEC_026 | Normalização de Horário Brasileiro no Painel e APIs | Concluída |
| [SPEC_027_TELEMETRIA_NO_SIGNAL_DASHBOARD/](SPEC_027_TELEMETRIA_NO_SIGNAL_DASHBOARD/SPEC.md) | SPEC_027 | Telemetria de No-Signal no Dashboard | Concluída |

---

## 🔗 Conexão com Outros Documentos

```text
MANIFESTO.md (Visão, Princípios)
    ↓
PRD.md (Requisitos de Negócio)
    ↓
SDD/ (Especificação Técnica) ← VOCÊ ESTÁ AQUI
    ├─ SPEC.md                              ← arquitetura geral
    ├─ SPEC_TEMPLATE.md                     ← template de novas specs
    ├─ MCP_SERENA_FLOW.md                   ← pipeline oficial por agentes
    ├─ SPEC_001_PAINEL_POSICOES_TEMPO_REAL/
    │   └─ SPEC.md
    ├─ SPEC_002_FRONTEND_CONSULTA_POSICOES/
    │   └─ SPEC.md
    ├─ SPEC_003_INCLUSAO_CALCULOS_MARGEM_POSICOES/
    │   └─ SPEC.md
    ├─ SPEC_004_NOTIFICACOES_TELEGRAM_OPERACIONAIS/
    │   └─ SPEC.md
    ├─ SPEC_006_RELATORIO_PERFORMANCE_TRADES/
    │   └─ SPEC.md
    ├─ ARCHITECTURE.md
    ├─ DATA_MODELS.md
    ├─ ERROR_HANDLING.md
    └─ SECURITY_DESIGN.md
    ↓
STRATEGY.md (Especificação da Estratégia BO Williams)
    ↓
src/ (Implementação)
    ├─ src/strategy/
    ├─ src/trading/
    ├─ src/exchange/
    ├─ src/storage/
    └─ src/monitoring/
    ↓
tests/ (Validação)
    └─ testes verificam conformidade com SDD
```

---

## 📋 Checklist para Time B (Execução)

Ao receber artefatos do Time A:

- [ ] **Leia SPEC.md completamente**
- [ ] **Siga o pipeline em MCP_SERENA_FLOW.md** (Planner -> Task Graph -> Dev -> Validation -> Gate)
- [ ] **Siga o fluxo Superpowers da skill SDD** (Brainstorm -> Plano -> Testes -> Implementação -> Review)
- [ ] **Atualize memória operacional** em `.ai/memory/project.md`, `.ai/memory/decisions.md`, `.ai/memory/corrections.md` e `.ai/memory/prompts.md`
- [ ] **Valide que PR code está em conformidade** (checklist em SPEC.md)
- [ ] **Execute testes parametrizados** (verificam contratos em SDD)
- [ ] **Atualize SDD se descobrir gap** (rastrear em Discussions)
- [ ] **Não implemente fora de SDD** — se não está em SDD, não está em escopo

---

## 🎯 Princípios de SDD

1. **Completo:** Engenheiro não precisa "adivinhar" — tudo está especificado
2. **Verificável:** Cada requisito em SDD tem teste correspondente
3. **Executável:** Possível começar implementação sem perguntas
4. **Vivo:** Atualizado conforme evolução (com versionamento)
5. **Rastreável:** Cada componente mapeia para requisito em PRD e princípio em MANIFESTO

## 📌 Semântica Canônica de Status

- **Em Refinamento:** escopo especificado, sem implementação validada.
- **Em Execução:** implementação parcial validada, com pendências abertas.
- **Concluída:** DoD atendido com evidências de código/testes/documentação.

---

## 📝 Como Usar Este SDD

### Para Implementadores

1. Leia [SPEC.md](SPEC.md) — entenda a arquitetura
2. Focalize no componente que você vai implementar
3. Siga interface e contrato exato
4. Quando descobrir ambiguidade, atualize SDD (não o código)

### Para Reviewers

1. Valide PR contra SPEC.md checklist
2. Se implementação diverge de SDD, é defeito (reject)
3. Se SDD é ambíguo, escale para Time A

### Para Product Owners

1. SDD = "prova técnica" de que PRD é viável
2. Se SDD identifica impossibilidade, feedback para Time A
3. Use como "aceitação técnica" antes de release

### Para Risk Manager / Auditor

1. SECURITY_DESIGN.md = conformidade de acesso e secrets
2. ERROR_HANDLING.md = mitigação de riscos operacionais
3. DATA_MODELS.md = rastreabilidade de auditoria

---

## 🚀 Próximos Passos

**Semana 1:**

- [ ] Equipe lê SPEC.md completo
- [ ] Feedback no [Discussions](https://github.com/jadergreiner/binance-phicube/discussions)
- [ ] Time A refina baseado em gaps

**Semana 2:**

- [ ] Time B começa implementação de Signal Engine
- [ ] ARCHITECTURE.md e DATA_MODELS.md são criados
- [ ] Primeiros PRs referem SPEC.md

---

## 📞 Governança

### Atualização de SDD

- **Correção de typo:** Direto (commit `docs(sdd): fix typo...`)
- **Clarificação sem mudança de comportamento:** Direto
- **Novo requisito/comportamento:** Requer Time A + Risk Manager
- **Remoção de recurso:** Requer aprovação do Product Owner

### Versionamento

- Versão incrementa com mudanças significativas
- Histórico preservado em git
- Tag releases alinhadas com releases de código

---

**Este SDD é o coração técnico do Binance Phicube. Toda implementação flui dele.**

*Mantido por: Backend Sênior + Quant Developer*
*Governado por: Time A (Refinamento) + Risk Manager*
