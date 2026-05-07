# SPEC_015 — Monitoramento de SL Órfão: Loop de Alertas, Auditabilidade e Guia de Intervenção

**ID:** SPEC_015
**Status:** Concluída
**Data:** 2026-05-05
**Autor:** Time A (Refinamento)
**Executores:** Time B (Execução) — Backend Sênior + QA
**Skills requeridas:** Python, asyncio, motor, structlog, pytest
**Depende de:** SPEC_012 (OrderMonitor e SLMissingEvent — base obrigatória)

---

## 1. Título e Resumo

### 1.1 Nome da Funcionalidade

Monitoramento de SL Órfão — Loop de Alertas, Auditabilidade e Guia de Intervenção.

### 1.2 Resumo (High-Level Definition)

**O que é:** Extensão do `OrderMonitor` (SPEC_012) que adiciona três capacidades: (1) re-notificação periódica enquanto a posição continuar desprotegida, evitando que o primeiro alerta seja ignorado; (2) registro no MongoDB do tempo de resposta do operador — intervalo entre o primeiro alerta e a restauração da proteção; (3) guia de intervenção documentado para o operador executar quando receber o alerta.

**Por que estamos fazendo:** A SPEC_012 envia um único alerta quando o SL desaparece (guard de duplicata). Isso é insuficiente: o operador pode estar dormindo, com o telefone no silencioso, ou simplesmente não agir. Uma posição sem SL em mercado volátil pode resultar em liquidação total. O loop de re-notificação é a última linha de defesa antes da intervenção manual.

**Valor de negócio:** Reduz o tempo médio de posição desprotegida; cria rastreabilidade de resposta do operador para análise posterior; dota o operador de um guia de ação claro reduzindo paralisia decisória em momento de stress.

**Conexão com PRD/SPEC:** PRD §Princípios — "proteção de todas as posições abertas" e "operador sempre informado de situações críticas"; SPEC_012 §2.2 — "Recolocação automática de SL fora de escopo (DD-002): operador decide" — esta SPEC não inverte essa decisão, apenas garante que o operador seja notificado até agir.

---

## 2. Objetivos e Escopo

### 2.1 Objetivos (o que será entregue)

- [ ] Loop de re-notificação: alerta repetido a cada `SL_MISSING_RENOTIFY_INTERVAL` minutos enquanto SL ausente
- [ ] Contador de re-notificações por `trade_id` (quantas vezes o alerta foi repetido)
- [ ] Registro no MongoDB: `sl_missing_first_detected_at`, `sl_restored_at`, `sl_missing_response_time_seconds`
- [ ] Limpeza do estado de re-notificação quando SL for restaurado ou posição encerrada
- [ ] Guia de intervenção documentado em `docs/OPERATIONS.md` — ações passo a passo para o operador
- [ ] Testes unitários cobrindo todos os novos cenários (mínimo 8 testes)

### 2.2 Fora do Escopo (Non-Goals)

- **Não inclui:** Recolocação automática de SL (herdado de DD-002 da SPEC_012 — decisão permanente)
- **Não inclui:** Escalonamento para canal diferente (e-mail, SMS) após N alertas sem resposta
- **Não inclui:** Bloqueio automático de novas posições enquanto houver SL órfão ativo
- **Não inclui:** Modificação da lógica de detecção de SL ausente — apenas da camada de notificação e registro

---

## 3. Referências

| Documento | Seção | Relevância |
|---|---|---|
| `SPEC_012` | §5.4, §5.5, §6 RF-001, §7 DD-002, DD-003 | Base do OrderMonitor, SLMissingEvent, guard de duplicata |
| `SPEC_004` | §4, §7.1 | Padrão de notificação Telegram crítica |
| `SPEC_007` | §5.1 | Padrão de retry e logs seguros |
| `src/monitoring/order_monitor.py` | `_handle_sl_missing` | Ponto de extensão desta SPEC |
| `src/storage/repository.py` | `update_trade_status` | Contrato de atualização MongoDB |

---

## 4. Design da Extensão sobre SPEC_012

### 4.1 Mudanças no Guard de Notificação

A SPEC_012 define `_notified_sl_missing: set[str]` como guard de uma única notificação por `trade_id`. Esta SPEC substitui esse guard por uma estrutura mais rica:

```python
# Substituição do set simples por dict com estado completo
_sl_missing_state: dict[str, SLMissingState]

@dataclass
class SLMissingState:
    trade_id: str
    first_detected_at: datetime
    last_notified_at: datetime
    notification_count: int
    renotify_interval_seconds: int
```

### 4.2 Lógica de Re-notificação

```text
Para cada trade com SL ausente detectado no ciclo atual:

  SE trade_id NÃO está em _sl_missing_state:
    → primeiro alerta: notificar, registrar first_detected_at, salvar estado
    → persiste sl_missing_first_detected_at no MongoDB

  SE trade_id ESTÁ em _sl_missing_state:
    → calcular: tempo_desde_ultimo_alerta = now - last_notified_at
    SE tempo_desde_ultimo_alerta >= renotify_interval_seconds:
      → re-notificar com mensagem incluindo: contagem de alertas, tempo total desprotegido
      → incrementar notification_count
      → atualizar last_notified_at

Para cada trade que DEIXOU de ter SL ausente (restaurado ou encerrado):
  SE trade_id estava em _sl_missing_state:
    → calcular sl_missing_response_time_seconds = now - first_detected_at
    → persistir no MongoDB: sl_restored_at, sl_missing_response_time_seconds
    → remover de _sl_missing_state
    → enviar notificação informativa "SL restaurado" com tempo de resposta
```

### 4.3 Novo Campo no Documento de Trade (MongoDB)

Os seguintes campos são adicionados ao documento de trade quando relevante:

```json
{
  "sl_missing_first_detected_at": "2026-05-05T14:30:00Z",
  "sl_restored_at": "2026-05-05T14:47:00Z",
  "sl_missing_response_time_seconds": 1020,
  "sl_missing_notification_count": 3
}
```

### 4.4 Mensagem de Re-notificação

A mensagem de re-notificação deve incluir informação adicional em relação ao primeiro alerta:

```
[CRITICAL] SL ORPHAN — Re-alerta #3
Símbolo: BTCUSDT
Posição desprotegida há: 34 minutos
SL esperado em: $82.150,00
Preço atual: $82.890,00
Distância do SL: 0,90%
Ação requerida: veja guia em docs/OPERATIONS.md
```

### 4.5 Configuração

Nova variável de ambiente:

```
SL_MISSING_RENOTIFY_INTERVAL_MINUTES=15  # padrão: 15 minutos
```

Adicionada ao `src/config/settings.py` com validação `ge=5` (mínimo 5 minutos — evitar spam).

---

## 5. Requisitos Funcionais

| ID | Descrição | Prioridade |
|---|---|---|
| RF-001 | Re-notificar a cada `SL_MISSING_RENOTIFY_INTERVAL_MINUTES` enquanto SL ausente | Crítica |
| RF-002 | Mensagem de re-alerta inclui: contagem, tempo total desprotegido, distância do SL | Alta |
| RF-003 | Persistir `sl_missing_first_detected_at` no MongoDB no primeiro alerta | Alta |
| RF-004 | Persistir `sl_restored_at` e `sl_missing_response_time_seconds` quando SL restaurado | Alta |
| RF-005 | Persistir `sl_missing_notification_count` no MongoDB ao fechar o estado | Alta |
| RF-006 | Limpar estado de re-notificação quando posição for encerrada por qualquer motivo | Alta |
| RF-007 | Enviar notificação informativa quando SL for restaurado (estado normalizado) | Média |
| RF-008 | `SL_MISSING_RENOTIFY_INTERVAL_MINUTES` configurável via env com mínimo de 5 min | Alta |
| RF-009 | Estado `_sl_missing_state` resetado em startup (aceita falso alerta em restart) | Baixa |

---

## 6. Requisitos Não-Funcionais

| ID | Descrição |
|---|---|
| RNF-001 | Intervalo de re-notificação com mínimo de 5 minutos — validado no Pydantic settings |
| RNF-002 | `response_time_seconds` calculado com precisão de segundos (não minutos) |
| RNF-003 | Estado de re-notificação não persiste entre restarts (memória) — documentado como comportamento aceito |
| RNF-004 | Logs seguros: `type(exc).__name__` em todas as exceções de rede |
| RNF-005 | Falha ao persistir métricas de resposta no MongoDB não bloqueia o ciclo principal |

---

## 7. Cenários e Casos de Borda

| ID | Cenário | Comportamento Esperado |
|---|---|---|
| CE-001 | SL restaurado manualmente antes do próximo ciclo de re-notificação | Notificação informativa enviada; resposta registrada; estado limpo |
| CE-002 | Posição encerrada por CLOSED_MANUAL enquanto SL órfão ativo | Estado de re-notificação limpo; `sl_missing_response_time_seconds` registrado até o momento do fechamento |
| CE-003 | Bot reiniciado com SL ainda ausente | Primeiro alerta enviado novamente ao reiniciar (estado em memória perdido — comportamento documentado e aceito) |
| CE-004 | `SL_MISSING_RENOTIFY_INTERVAL_MINUTES=3` (abaixo do mínimo) | Settings falha na validação com erro descritivo antes de iniciar |
| CE-005 | Dois trades diferentes com SL órfão simultâneo | Estados independentes para cada `trade_id` — re-notificações não interferem |
| CE-006 | Falha no Telegram ao enviar re-alerta | Log warning; tenta novamente no próximo ciclo (não marca como notificado em caso de falha) |
| CE-007 | SL recolocado e cancelado novamente (oscilação) | Novo ciclo de re-notificação iniciado; `sl_missing_notification_count` acumulativo no mesmo documento de trade |

---

## 8. Guia de Intervenção para o Operador

O seguinte guia deve ser incluído em `docs/OPERATIONS.md`:

### Seção: Resposta a Alerta de SL Órfão

**Ao receber alerta de SL ORPHAN:**

1. Verifique se a posição ainda está aberta na Binance (Futures > Posições)
2. Se a posição foi fechada: o sistema detectará na próxima varredura e encerrará automaticamente os alertas
3. Se a posição está aberta:
   - Acesse Binance Futures > símbolo afetado
   - Verifique o preço atual e calcule manualmente o risco sem SL
   - Decida: recolocar SL ou fechar a posição manualmente
   - Para recolocar SL: crie ordem Stop Market no lado oposto à posição, com `reduceOnly=true`
   - Para fechar manualmente: use Market Order com `reduceOnly=true`
4. Após a ação, o sistema detectará a restauração no próximo ciclo de 60s e enviará confirmação

**Nunca ignore alertas de SL ORPHAN. Cada minuto sem proteção é risco não coberto.**

---

## 9. Critérios de Aceite e DoD

### Critérios de Aceite

```text
DADO   que um trade OPEN tem SL cancelado (detectado pelo OrderMonitor da SPEC_012)
QUANDO 15 minutos passam sem restauração
ENTÃO  um segundo alerta é enviado com contagem "#2" e tempo desprotegido
E      a cada 15 minutos subsequentes um novo alerta é enviado
E      o MongoDB registra sl_missing_first_detected_at no primeiro alerta

DADO   que o SL é restaurado (ordem SL ativa na exchange)
QUANDO o OrderMonitor detecta a restauração
ENTÃO  uma notificação informativa "SL restaurado" é enviada
E      sl_restored_at e sl_missing_response_time_seconds são persistidos no MongoDB
E      o estado de re-notificação é limpo

DADO   SL_MISSING_RENOTIFY_INTERVAL_MINUTES=3 no .env
QUANDO o sistema é iniciado
ENTÃO  Pydantic settings falha com ValidationError antes de qualquer conexão
```

### Definição de Pronto (DoD)

- [ ] `SLMissingState` dataclass implementado substituindo o set simples de SPEC_012
- [ ] Lógica de re-notificação implementada em `_handle_sl_missing` com intervalo configurável
- [ ] Campos `sl_missing_first_detected_at`, `sl_restored_at`, `sl_missing_response_time_seconds`, `sl_missing_notification_count` adicionados ao schema de trades
- [ ] `MongoRepository` atualizado com método para persistir métricas de SL órfão
- [ ] `SL_MISSING_RENOTIFY_INTERVAL_MINUTES` em `src/config/settings.py` com validação `ge=5`
- [ ] Notificação de restauração de SL implementada
- [ ] Guia de intervenção em `docs/OPERATIONS.md`
- [ ] Mínimo 8 testes em `tests/monitoring/test_sl_orphan_loop.py` passando
- [ ] `docs/SDD/README.md` atualizado com SPEC_015
- [ ] `ruff check src/ tests/` sem erros
- [ ] Nenhuma das invariantes da SPEC_012 §8 violada

---

## 10. Decisões de Design

| ID | Decisão | Justificativa |
|---|---|---|
| DD-001 | Estado de re-notificação em memória (não persistido) | Consistente com DD-003 da SPEC_012; complexidade de persistência do estado não justificada — falso alerta em restart é aceitável e documentado |
| DD-002 | Mínimo de 5 minutos para re-notificação | Abaixo disso é spam; em 5 minutos o operador já deveria ter visto o primeiro alerta |
| DD-003 | Registro de `response_time_seconds` no MongoDB | Cria dataset para análise futura: "quanto tempo em média o operador leva para responder?" — insumo para decisão futura de automação |
| DD-004 | Notificação de restauração de SL como informativa (não crítica) | Situação normalizada — alerta desnecessário aumenta fadiga de alerta |
| DD-005 | Recolocação automática de SL permanece fora de escopo | Herdado de DD-002 da SPEC_012; esta SPEC não revisa essa decisão de design |

---

## 11. Riscos

| Risco | Impacto | Probabilidade | Mitigação |
|---|---|---|---|
| Operador ignora todos os re-alertas e posição é liquidada | Crítico | Baixa | N/A — limite do sistema de alertas sem automação de fechamento |
| Loop de re-notificação com intervalo muito curto gera fadiga de alerta | Alto | Média | Mínimo de 5 min validado; padrão de 15 min é conservador |
| Falha no Telegram silencia todos os alertas | Alto | Baixa | SPEC_004 já cobre retry de Telegram |
| Acúmulo de estado em memória para muitos trades com SL órfão simultâneo | Baixo | Muito Baixa | Cada entry é mínimo (< 200 bytes); sem limite prático |

---

## Histórico

- **2026-05-05:** Criação da SPEC_015 pelo Time A como extensão direta da SPEC_012.
