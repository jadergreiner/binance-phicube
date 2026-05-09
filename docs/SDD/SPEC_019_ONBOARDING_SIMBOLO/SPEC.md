# SPEC_019 — Onboarding de Símbolo via Frontend

**ID:** SPEC_019  
**Título:** Onboarding de Símbolo — Wizard de Inclusão, Backtest e Aprovação para Produção  
**Status:** Concluída  
**Data:** 2026-05-06  
**Prioridade:** Alta  
**Autores:** Time A (Refinamento)

---

## 1. Objetivo

Permitir que o operador inclua um novo símbolo de trading diretamente pelo frontend do dashboard, passando por um fluxo guiado: preenchimento de parâmetros → execução de backtest → revisão dos resultados → aprovação para produção.

---

## 2. Problema Resolvido

Atualmente, adicionar um símbolo exige edição manual de `.env` e reinicialização do bot. Este processo é propenso a erros (alavancagem incorreta, timeframe inadequado) e não há validação prévia via backtest. A SPEC_019 introduz um fluxo de onboarding rastreável e auditável diretamente no dashboard.

---

## 3. Impacto

- **Negócio:** reduz risco de ativar símbolo sem evidência quantitativa
- **Técnico:** adiciona coleção MongoDB `symbol_onboarding`, 4 novos endpoints REST, nova seção no frontend
- **Operacional:** o bot ainda requer reinicialização manual após aprovação (arquitetura com `@lru_cache` em Settings)

---

## 4. Estado Atual do Limite de Backtest

O endpoint `GET /backtest` tinha limite máximo de 5000 candles — insuficiente para gerar amostra estatisticamente relevante (Trader Sênior exige ≥ 200 trades). A SPEC_019 eleva o limite para 60000 candles.

---

## 5. Máquina de Estados

```
CANDIDATE → BACKTESTED → APPROVED
```

| Estado | Significado |
|---|---|
| `CANDIDATE` | Sessão criada, parâmetros armazenados, aguardando backtest |
| `BACKTESTED` | Backtest concluído; métricas disponíveis para revisão |
| `APPROVED` | Operador aprovou; `config_string` gerada para inclusão no `.env` |

Transições de erro: se o backtest falhar (símbolo inválido, Binance indisponível), o status permanece `CANDIDATE` e `backtest_error` é preenchido.

---

## 6. Modelo de Dados — Coleção `symbol_onboarding`

```json
{
  "symbol":          "ATOMUSDT",
  "timeframe":       "15m",
  "leverage":        3,
  "status":          "BACKTESTED",
  "created_at":      "2026-05-06T10:00:00Z",
  "updated_at":      "2026-05-06T10:05:00Z",
  "backtest_result": { ...métricas... },
  "backtest_limit":  35000,
  "backtest_error":  null,
  "config_string":   null,
  "notes":           null
}
```

**Índices:**
- `{ symbol: 1 }` único — impede sessões duplicadas para o mesmo símbolo
- `{ status: 1, created_at: -1 }` — listagem por status

---

## 7. Endpoints REST

### `GET /onboarding`
Lista todas as sessões de onboarding.  
**Resposta:** `200 [ { ...sessão... } ]`

### `POST /onboarding`
Cria nova sessão de onboarding.  
**Body:** `{ symbol, timeframe, leverage }`  
**Validações:**
- `symbol` ∈ formato válido (maiúsculas, sufixo USDT, 4–20 chars)
- `timeframe` ∈ `{1m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d}`
- `leverage` ∈ `[1, 20]`
- Símbolo **não** pode estar já ativo (em `SYMBOL_TIMEFRAMES`)
- Não pode existir sessão com mesmo símbolo

**Resposta:** `201 { ...sessão criada... }` | `409` se duplicado | `422` se inválido

### `GET /onboarding/{symbol}`
Retorna sessão específica.  
**Resposta:** `200 { ...sessão... }` | `404`

### `DELETE /onboarding/{symbol}`
Remove sessão (qualquer estado).  
**Resposta:** `204` | `404`

### `POST /onboarding/{symbol}/backtest` (legado desativado)
Endpoint legado síncrono desativado.

**Contrato:**
- Sempre retorna `410 Gone`.
- Resposta inclui instrução de migração para:
  - `POST /onboarding/{symbol}/backtest-jobs`
  - `GET /onboarding/backtest-jobs/{job_id}`

### `POST /onboarding/{symbol}/backtest-jobs` (assíncrono)
Inicia job assíncrono de backtest para onboarding.
**Body (opcional):** `{ limit?, balance? }`
- `limit`: candles a buscar (50–60000, default 35000)
- `balance`: saldo simulado USDT (default 1000)

**Contrato:**
- Retorna `202 Accepted` com `job_id`, `status` e metadados de rastreamento.
- Se existir job ativo (`queued`/`running`) para a mesma chave lógica (`symbol`, `timeframe`, `limit`, `balance`), retorna o job ativo existente e `reused_active_job=true`.

**Resposta:** `202 { job_id, status, symbol, timeframe, ... }` | `404` | `409`

### `GET /onboarding/backtest-jobs/{job_id}` (assíncrono)
Consulta estado e resultado de job de backtest.

**Estados permitidos:** `queued`, `running`, `succeeded`, `failed`, `canceled`

**Contrato:**
- Em sucesso, retorna `backtest_result`.
- Em falha, retorna `error_code` e `error_message`.

**Resposta:** `200 { ...job... }` | `404`

### `POST /onboarding/{symbol}/approve`
Aprovação manual do operador.  
**Body (opcional):** `{ notes? }`  
**Pré-condição:** status deve ser `BACKTESTED`  
**Ação:** gera `config_string = "SYMBOL:TIMEFRAME:LEVERAGE"`, status → `APPROVED`  
**Resposta:** `200 { ...sessão com config_string..., operational_checklist: [...] }` | `404` | `409` (não está em BACKTESTED)

**Checklist operacional pós-aprovação (operational_checklist):**
1. Adicionar `config_string` em `SYMBOL_TIMEFRAMES` no `.env`
2. Reiniciar o bot para aplicar o novo símbolo
3. Validar sessão via `GET /onboarding` e monitorar `GET /health` no dashboard

---

## 8. Segurança

**Limitação conhecida:** o dashboard não possui autenticação — os endpoints de escrita (`POST`, `DELETE`) são acessíveis sem credenciais. Como o dashboard é implantado localmente (localhost), o risco é aceitável para a fase atual. Autenticação será endereçada em SPEC futura.

---

## 9. Frontend — Seção de Onboarding

Nova seção `<section class="onboarding-panel">` ao final de `index.html`:

**Passo 1 — Novo Símbolo:** formulário com inputs `symbol`, `timeframe`, `leverage`.  
**Passo 2 — Sessões Ativas:** tabela com colunas: Símbolo, Timeframe, Leverage, Status, Trades, Win Rate, PF, Drawdown, Criado em, Ações.  
**Ações por linha:**
- `CANDIDATE` → botão "Rodar Backtest"
- `BACKTESTED` → botão "Aprovar" + badge com métricas
- `APPROVED` → exibe `config_string` copiável + instruções de ativação

---

## 10. Restrições Técnicas

1. **Bot restart obrigatório:** após aprovação, o operador deve manualmente adicionar o `config_string` ao `.env` e reiniciar o bot. O dashboard exibe instruções claras.
2. **Limite de backtest:** max 60000 candles. Operações longas (60000 × 15m ≈ 625 dias) podem levar ~60s.
3. **Commodity gate:** se o símbolo for commodity (`XPTUSDT`, `COPPERUSDT`), o `config_string` incluirá comentário alertando para definir `COMMODITIES_BACKTEST_VALIDATED=true`.
4. **Backtest assíncrono-only:** o fluxo oficial de backtest no onboarding é exclusivamente por jobs assíncronos (`/backtest-jobs`).
5. **Endpoint legado desativado:** chamadas para `/onboarding/{symbol}/backtest` retornam `410 Gone` com instrução de migração.

---

## 11. Critérios de Aceite

- [ ] `POST /onboarding` retorna 409 se símbolo já está em `SYMBOL_TIMEFRAMES` ativos
- [ ] `POST /onboarding` retorna 409 se sessão com mesmo símbolo já existe
- [ ] `POST /onboarding/{symbol}/backtest-jobs` retorna `202` com `job_id` e estado inicial
- [ ] `GET /onboarding/backtest-jobs/{job_id}` retorna estado terminal e `backtest_result` quando `succeeded`
- [ ] `POST /onboarding/{symbol}/backtest` retorna `410 Gone` com instrução de migração
- [ ] `POST /onboarding/{symbol}/approve` gera `config_string` no formato correto
- [ ] Frontend exibe sessões, permite rodar backtest e aprovar via botões
- [ ] `GET /backtest` aceita `limit` até 60000
- [ ] Testes: `tests/api/test_onboarding.py` com ≥ 8 casos

---

## 12. Rastreabilidade

| Requisito | Componente | Teste |
|---|---|---|
| Criar sessão | `POST /onboarding` | `test_criar_sessao_candidata` |
| Rejeitar duplicado (ativo) | `POST /onboarding` | `test_rejeitar_simbolo_ja_ativo` |
| Rejeitar duplicado (sessão) | `POST /onboarding` | `test_rejeitar_sessao_duplicada` |
| Criar job assíncrono | `POST /onboarding/{symbol}/backtest-jobs` | `test_backtest_transiciona_para_backtested` |
| Consultar job assíncrono | `GET /onboarding/backtest-jobs/{job_id}` | `test_consulta_job_por_id` |
| Legado desativado | `POST /onboarding/{symbol}/backtest` | `test_backtest_legado_retorna_410_com_migration` |
| Aprovar sessão | `POST /onboarding/{symbol}/approve` | `test_aprovar_gera_config_string` |
| Config string correta | `POST /onboarding/{symbol}/approve` | `test_config_string_formato` |
| Listar sessões | `GET /onboarding` | `test_listar_sessoes` |
| Deletar sessão | `DELETE /onboarding/{symbol}` | `test_deletar_sessao` |
