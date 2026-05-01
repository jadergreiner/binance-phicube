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

### Core Documents (em ordem de leitura)

1. **[SPEC.md](SPEC.md)** — Especificação técnica completa (⭐ comece aqui)
   - Arquitetura geral
   - Componentes: Signal Engine, Risk Manager, Order Manager, Storage, Logger, Exchange Integration
   - Interfaces e contratos
   - Fluxos de dados e sequências
   - Padrões de design

2. **ARCHITECTURE.md** *(em breve)* — Diagrama de arquitetura profundo
   - Camadas (domain, application, infrastructure)
   - Dependências entre módulos
   - Runtime topology

3. **DATA_MODELS.md** *(em breve)* — Esquema de dados
   - Estruturas de Signal, Trade, Position
   - MongoDB collections e indexes
   - Serialização

4. **ERROR_HANDLING.md** *(em breve)* — Estratégia de falhas
   - Erros recuperáveis vs. fatais
   - Retry logic, circuit breakers
   - Logging estruturado

5. **SECURITY_DESIGN.md** *(em breve)* — Design de segurança
   - Gerenciamento de secrets
   - Acesso e permissões
   - Auditoria

---

## 🔗 Conexão com Outros Documentos

```text
MANIFESTO.md (Visão, Princípios)
    ↓
PRD.md (Requisitos de Negócio)
    ↓
SDD/ (Especificação Técnica) ← VOCÊ ESTÁ AQUI
    ├─ SPEC.md
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
