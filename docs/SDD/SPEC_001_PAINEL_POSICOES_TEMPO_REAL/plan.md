# Plan — SPEC_001: Painel de Posições em Tempo Real

**spec_id:** SPEC_001
**status:** Pronto para tasks
**data:** 2026-05-01
**autor:** Time A (Refinamento)

---

## Meta

- **spec_id:** SPEC_001
- **objetivo:** Entregar painel somente leitura de posições abertas Binance Futures USDT-M com atualização em tempo quase real (≤2s normal, ≤12s degradado) e sinalização explícita de degradação de dados.
- **escopo:** Leitura de posições, resumo agregado de risco, stream + fallback adaptativo, status de conexão, stale data.
- **fora_de_escopo:** Fechar posição, alterar SL/TP, histórico de fechamentos, alertas automáticos, IA de recomendação.

---

## Decisões Arquiteturais (Time A — sessão 2026-05-01)

| Decisão | Escolha | Justificativa |
|---|---|---|
| Fonte primária de dados | Binance direta (WebSocket `userData` stream) | MongoDB tem defasagem cumulativa; `mark_price` e `unrealized_pnl_usdt` mudam a cada tick e o bot não grava a cada tick. |
| Papel do MongoDB | Cache frio de último snapshot válido | Usado apenas para recuperação de contexto pós-restart do painel, não como fonte de leitura em tempo real. |
| API Key do painel | Key dedicada READ_ONLY (sem permissão de trade) | Isola vetor de risco da Key de trade do bot. Pré-requisito bloqueante. |
| Fallback por polling | Adaptativo: 2s nos primeiros 30s → 10s após estabilização | Reduz janela de stale no momento crítico da transição sem pressionar rate limit estruturalmente. |
| Exibição em modo degradado | PnL e mark_price exibem `—` (não valor stale) | Dado stale exibido como atual é pior que nenhum dado — cria ilusão de controle operacional. |

---

## Entradas

- `docs/SDD/SPEC_001_PAINEL_POSICOES_TEMPO_REAL/SPEC.md`
- `contracts/task.json` (template de contrato de task)
- Credenciais de API Key READ_ONLY configuradas no ambiente (`.env`)

---

## Premissas

- A Binance Testnet suporta `userData` stream para posições Futures USDT-M.
- O bot principal opera com API Key separada (permissão de trade); o painel usa Key exclusiva READ_ONLY.
- O MongoDB (motor) já está disponível como dependência do projeto.
- O operador tem acesso à UI via interface local ou rede isolada — sem exposição pública no MVP.
- `listenKey` do WebSocket deve ser renovado a cada 30–60 minutos (responsabilidade do painel, não do bot).

---

## Riscos e Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| API Key do painel com permissão de trade por engano | Alto | Key configurada como READ_ONLY no momento da criação; validada por task de segurança (AppSec) antes de qualquer execução. |
| `listenKey` expirar sem renovação | Alto | Implementar keepalive assíncrono a cada 30min com tratamento de falha e reconexão automática. |
| Polling adaptativo pressionar rate limit durante degradação prolongada | Médio | Limite de 2s por 30s = 75 pesos/min (seguro). Monitorar header `X-MBX-USED-WEIGHT` e recuar se >80% do limite. |
| Dados do MongoDB divergentes após restart | Médio | MongoDB é apenas cache de contexto; ao iniciar, sempre sincronizar com snapshot REST antes de exibir qualquer dado. |
| Escopo inflar com features não-MVP (ex: fechar posição pela UI) | Médio | Enforçar non-goals da SPEC; qualquer adição requer nova SPEC aprovada pelo Time A. |
| Operador confundir modo degradado com modo normal | Alto | Banner explícito + campos PnL exibindo `—` + alerta sonoro/visual obrigatório na transição. US-001-03 é controle de risco, não feature opcional. |

---

## Estratégia de Execução

As fases são **sequenciais** — cada fase é pré-requisito da seguinte.

### Fase 1 — Infraestrutura de Acesso (pré-requisito bloqueante)

- Configurar API Key READ_ONLY dedicada ao painel no `.env`.
- Implementar cliente ccxt async para o painel (separado do bot).
- Validar que a Key não possui permissão de trade (task AppSec obrigatória).

### Fase 2 — Camada de Dados

- Implementar conexão WebSocket `userData` stream (posições e conta).
- Implementar snapshot inicial via REST `/fapi/v2/positionRisk` na inicialização.
- Implementar persistência do último snapshot válido no MongoDB (cache frio).
- Definir e validar contrato de dados de posição (campos, tipos, `updated_at`).

### Fase 3 — Motor de Atualização e Resiliência

- Implementar polling adaptativo: 2s por 30s → 10s após estabilização.
- Implementar detecção de stale data (ausência de update dentro da janela).
- Implementar reconciliação: ao restaurar stream, sincronizar com snapshot REST.
- Implementar `listenKey` keepalive assíncrono.
- Implementar monitoramento de `X-MBX-USED-WEIGHT` para proteção de rate limit.

### Fase 4 — Interface de Visualização

- Implementar tabela de posições com campos obrigatórios da SPEC.
- Implementar card de resumo agregado (exposição total, margem, PnL total).
- Implementar indicador de status de conexão (online / degradado / offline).
- Implementar exibição de `—` em PnL e mark_price no modo degradado.
- Implementar banner + alerta sonoro/visual na transição para modo degradado.
- Confirmar que a UI não possui nenhuma ação de trade (somente leitura).

### Fase 5 — Testes e Validação

- Testes unitários: mapeamento de posição, cálculo de resumo, detecção de stale.
- Testes de integração (Testnet): stream ativo, queda de stream + fallback, reconciliação.
- Evidências obrigatórias conforme SPEC seção 7.3.

---

## Dependências

- API Key READ_ONLY criada na Binance Testnet (dependência externa — operador).
- MongoDB disponível e acessível (já disponível no projeto).
- ccxt async configurado (já disponível no projeto).
- Testnet com posições abertas para validação de integração (dependência do operador).

---

## Critérios de Pronto do Plano

- [x] Plano rastreável para a SPEC_001.
- [x] Decisões arquiteturais registradas com justificativa.
- [x] Dependências mapeadas.
- [x] Riscos com mitigação definida.
- [x] Fases sequenciais com pré-requisitos claros.
- [x] Pronto para gerar `tasks.json`.
