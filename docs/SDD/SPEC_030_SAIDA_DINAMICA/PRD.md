# PRD — Saída Dinâmica: Trailing Stop e Take-Profit Parcial

**Documento:** Product Requirements Document
**Feature:** Saída Dinâmica — TP Parcial (V1) + Trailing Stop (V2)
**SPEC vinculada:** `SPEC_030_SAIDA_DINAMICA/SPEC.md` (v2.0)
**PRD raiz:** `PRD.md` § Fase 2 — "Estratégia de saída avançada"
**Data:** 2026-05-11
**Versão:** 1.0
**Status:** Aprovado

---

## 1. Sumário Executivo

Hoje o bot fecha cada posição com **SL e TP fixos** calculados na abertura. O operador não tem como capturar tendências prolongadas (preço dispara além do TP fixo) nem realizar lucro parcial (50% no TP1, deixa o resto correr). Para fazer isso, precisaria monitorar manualmente — reintroduzindo o componente emocional que o bot deveria eliminar.

**Saída Dinâmica resolve isso com dois mecanismos independentes:**

| Mecanismo | Descrição | Valor |
|-----------|-----------|-------|
| **TP Parcial (V1)** | Envia até 3 níveis de take-profit na abertura. Cada nível fecha um percentual da posição. Zero intervenção do bot depois. | Realiza lucro parcial sem timing risk. Saldo médio mais estável. SL original nunca é movido. |
| **Trailing Stop (V2)** | Stop que acompanha o preço automaticamente via ordem nativa TRAILING_STOP_MARKET da Binance. Sem risco de gap (ordem MARKET). | Protege ganhos em tendências fortes sem intervenção manual. |

---

## 2. Problema que Resolve

| Problema | Impacto Hoje | Como Saída Dinâmica Resolve |
|----------|-------------|-----------------------------|
| **Tendência longa subaproveitada** | BTC sobe 8%, TP fixo em 3% fecha tudo. Operador perdeu 5% de lucro potencial. | TP parcial: 50% fecha no TP1 (3%), 50% corre até TP2 (6%). Ou trailing stop captura toda a tendência. |
| **Reenvio de SL pós-TP1 (risco operacional)** | Rascunho original previa reenviar SL para break-even. Se a API falha ou o preço gapa, posição fica sem proteção. | TP parcial usa ordens reduceOnly: exchange gerencia. SL original nunca sai. |
| **Acompanhamento manual do stop** | Operador abre Telegram, olha posição, pensa "será que já devo sair?". Decisão emocional. | Trailing stop nativo da Binance: bot cria uma vez, exchange gerencia. Zero intervenção. |
| **Stop não executado em gap** | SL em LIMIT pode não executar em movimentos bruscos. | TRAILING_STOP_MARKET executa como MARKET — sem risco de não-execução. |
| **Lucro realizado vs. posição que virou perda** | Posição sobe 5%, operador não realiza, cai e bate no SL com perda. | TP parcial garante que parte do lucro seja realizado. |

### Cenário Ilustrativo

| Situação | Hoje (fixed) | Com TP Parcial | Com Trailing |
|----------|-------------|----------------|--------------|
| BTC sobe 3% e cai | Fecha em TP: +3% no total | TP1 (2%): fecha 50%. Restante cai pra SL: perde 0. | Trailing nunca ativou (threshold 3%): SL protege. |
| BTC sobe 6% | Fecha em TP: +3% no total | TP1 (2%): 50%. TP2 (4%): 50%. Lucro médio ~3% igual. | Trailing ativa em 3%, segue até 6%, trava lucro. |
| BTC sobe 12% | Fecha em TP: +3% no total | TP1 (2%): 50%. TP2 (4%): 50%. Lucro médio ~3%. Perdeu 9% de oportunidade. | Trailing segue até o topo (12%), callback 0.5% → saída em ~11.5%. **Capturou a tendência.** |

---

## 3. Valor para o Operador

1. **Zero intervenção pós-abertura:** todas as ordens de saída são enviadas junto com a entrada. A exchange gerencia ajustes, reduções e execução. O bot não toca mais na posição.
2. **Lucro parcial garantido:** TP parcial realiza parte do lucro mesmo que a posição reverta. Menos trades no vermelho.
3. **Captura de tendências:** trailing stop nativo permite surfar movimentos fortes sem o risco de um stop LIMIT não executar.
4. **Segurança operacional:** SL original nunca é removido ou reenviado (DD-002). Risco zero de posição desprotegida.
5. **Transparência total:** cada TP executado é logado com nível, preço, quantidade e condição de mercado. Auditável.

---

## 4. Personas Impactadas

### Operador (primário)
- **Necessidade:** Capturar tendências e realizar lucro sem reintroduzir emoção na operação
- **Ganha:** O bot gerencia a saída inteira — da abertura ao fechamento completo — sem precisar de acompanhamento
- **Perde se não fizermos:** Continua perdendo lucro potencial em tendências e tendo que decidir manualmente quando sair

### Desenvolvedor (secundário)
- **Necessidade:** Implementação simples e segura, sem estado pós-abertura para gerenciar
- **Ganha:** Zero lógica de pós-processamento. Algoritmo linear (N ordens na abertura, depois silêncio). Fácil de testar.
- **Perde se não fizermos:** Implementação complexa com reenvio de ordens, polling de posição, risco de race condition

---

## 5. Critérios de Sucesso

| Critério | Métrica | Alvo | Como Verificar |
|----------|---------|------|----------------|
| **TP parcial executa corretamente** | Níveis executam na ordem, SL não é movido | 100% das execuções em Testnet | TEST_030_01 a 04 |
| **Zero reenvio de SL** | Nenhuma chamada de cancelamento/recolocação de SL | 0 eventos pós-abertura | Logs de auditoria |
| **Trailing stop nativo (V2)** | TRAILING_STOP_MARKET ativa e executa na Algo Order API | Confirmado em Testnet | Chamada direta ao `POST /fapi/v1/algo` |
| **Config validation** | Config inválida causa erro fatal no startup | 100% dos casos de borda | TEST_030_06 a 08 |
| **Simulação compatível** | SimulatedBinanceClient executa TP parcial | Mesmo resultado que modo real | TEST_030_05 |
| **Modo legado intacto** | `exit_strategy="fixed"` → comportamento atual | Zero mudança | Testes comparativos |

---

## 6. Decisões de Produto

### Tomadas no refinamento

| Decisão | Opção Escolhida | Alternativa Rejeitada | Motivo |
|---------|----------------|----------------------|--------|
| Arquitetura TP Parcial | Ordens reduceOnly nativas na abertura (D-001) | Reenvio de SL pós-TP1 (rascunho original) | Risco operacional de SL órfão é inaceitável (DD-002) |
| Mecanismo de Trailing (V2) | TRAILING_STOP_MARKET nativo via Algo Order API (D-002) | TAKE_PROFIT_LIMIT móvel (rascunho original) | Risco de não-execução em gap. Ordem MARKET resolve. |
| Modo padrão | `"fixed"` (D-003) | Qualquer modo dinâmico como default | Operador não deve ter surpresa na atualização |
| Trailing adaptativo | Rejeitado (D-005) | callbackRate variável por ATR | Cancelar/recriar ordens introduz latência e risco |
| Config inválida | Erro fatal (D-006) | Warning silencioso | Posição com config errada = perda de capital |
| RRR para TP parcial | Média ponderada por quantidade (D-007) | RRR do último nível apenas | Subestimaria ou superestimaria o RRR realizado |
| Logging | Nível, preço, qty remanescente, mercado (D-008) | Logging mínimo | Sem logging detalhado, operador não sabe o que aconteceu |

### Em aberto (V2 condicional)

| Decisão | Responsável | Prazo |
|---------|-------------|-------|
| TRAILING_STOP_MARKET funcional na Testnet? | Backend Sênior (verificar) | Antes de implementar V2 |
| ccxt versão atual suporta? | Backend Sênior (verificar) | Durante verificação técnica |
| callbackRate ideal por símbolo | Trader Sênior (homologar) | Pós-rollout V1 |

---

## 7. Conformidade com o Manifesto

| Princípio | Como SPEC_030 atende |
|-----------|---------------------|
| 1. Disciplina | Saída 100% automatizada na abertura. Zero decisão manual durante a posição. |
| 2. Gestão de risco | SL original nunca é removido (DD-002). TP parcial só reduz posição. |
| 3. Transparência | Cada TP executado é logado com contexto completo. RRR médio ponderado. |
| 4. Configurabilidade | Estratégia de saída configurável por símbolo. Fallback global para "fixed". |
| 5. Segurança | Sem impacto — não envolve credenciais. Chamada Algo Order API usa mesma auth. |
| 6. Resiliência | Zero pós-processamento = zero pontos de falha. Exchange gerencia. |
| 7. Evolução baseada em dados | RRR médio ponderado alimenta métricas de performance (SPEC_006). |

---

## 8. Risco e Rollout

### Estratégia de rollout

1. **V1 — TP Parcial (obrigatório):**
   - Testes unitários (TEST_030_01 a 09)
   - Simulação via SimulatedBinanceClient
   - `exit_strategy="fixed"` como default — operador ativa manualmente
   - Rollout por símbolo via `.env`

2. **Verificação técnica (pré-V2):**
   - Testar ccxt + Algo Order API na Testnet
   - Confirmar TRAILING_STOP_MARKET funcional
   - Relatar resultado

3. **V2 — Trailing Stop (condicional):**
   - Implementar `create_trailing_stop_order()` via REST direta
   - Se Testnet não suporta, aceitar risco em produção documentado

### Riscos conhecidos

| Risco | Probabilidade | Impacto | Mitigação |
|-------|--------------|---------|-----------|
| ccxt desatualizado não suporta Algo Order API | Alta (versão atual desconhecida) | Alto — V2 bloqueada | Chamada REST direta ao `POST /fapi/v1/algo` |
| Testnet não suporta TRAILING_STOP_MARKET | Média | Médio — V2 não testável | Documentar risco; aceitar em produção se documentação confirmar |
| Config complexa confunde operador (4 modos + N níveis) | Baixa | Baixo | Default = "fixed". Documentação clara. |

---

## 8. Fora de Escopo (v1)

- Re-entrada após TP parcial (será SPEC separada)
- Modo `"partial+trailing"` combinado (futuro)
- Trailing adaptativo por ATR (ciclo futuro)
- Gestão visual no frontend
- Cancelamento automático de trailing stop (DD-002: SL nunca recolocado)

---

## 9. Conexão com PRD Principal

Este PRD_030 é uma **especificação de feature** que complementa o [`PRD.md`](../../PRD.md) principal:

- **PRD.md § Fase 2:** novo item "Estratégia de saída avançada" adicionado
- **PRD.md § MVP Fase 1 (Execução de Ordem):** a seção atual descreve SL + TP fixos — TP parcial é extensão natural, mantendo compatibilidade reversa
- **PRD.md § Configuração User-facing:** novos parâmetros `EXIT_STRATEGY`, `TP_LEVELS`, `TRAILING_ACTIVATION_PCT`, `TRAILING_CALLBACK_RATE`
- **PRD.md § Riscos:** adicionado "Config complexa confunde operador" mitigado pelo default `"fixed"`
- **PRD.md v1.2** já reflete essas atualizações

### Atualizações realizadas no PRD Principal

| O quê | Onde |
|------|------|
| Item "Estratégia de saída avançada" adicionado | PRD.md § Fase 2 |
| Subseção detalhada com problema, solução, critérios e config | PRD.md § Fase 2 (nova) |
| Versão incrementada | 1.1 → 1.2 |
| Histórico atualizado | Linha `1.2 | 2026-05-11 | Time A | SPEC_030` |

---

## 10. Histórico

| Versão | Data | Autor | Mudanças |
|--------|------|-------|----------|
| 1.0 | 2026-05-11 | Time A (Refinamento) | Documento inicial pós-sessão de refinamento e convergência SPEC_030 |
