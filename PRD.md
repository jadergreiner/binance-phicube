# PRD — Product Requirement Document — Binance Phicube

**Versão:** 1.0
**Data de Criação:** 2026-05-01
**Proprietário:** Equipe Phicube
**Status:** Ativo — Refinamento Contínuo

---

## 📋 Sumário Executivo

O **Binance Phicube** é uma ferramenta pessoal de auto trade que executa a estratégia **BO Williams (Phicube)** de forma automática, disciplinada e auditável na corretora Binance.

**Objetivo primário:** Remover o componente emocional das decisões de entrada e saída do próprio operador, garantindo execução sistemática e fiel ao método 24/7.

**Natureza:** Sistema de uso pessoal — opera com um único conjunto de credenciais Binance, em instância única, para o próprio dono. Não é uma plataforma multi-usuário.

---

## 🎯 O QUÊ — Definição do Produto

### Declaração de Produto

Uma **ferramenta pessoal de automação de trade** que:

1. **Monitora continuamente** símbolos (pares cripto) na Binance em tempo real
2. **Detecta sinais válidos** conforme as regras objetivas da estratégia Phicube
3. **Executa operações automaticamente** (entrada, stop loss, take profit) sem intervenção manual
4. **Registra e audita** toda decisão do próprio operador, permitindo análise de desempenho e revisão de conformidade com o método

### Componentes Principais

| Componente | Descrição | Responsabilidade |
|---|---|---|
| **Signal Engine** | Detecta sinais LONG/SHORT baseado em Alligator + AO + Fractais | Identificação objetiva de entrada |
| **Risk Manager** | Calcula posição de forma proporcional ao risco configurado | Proteção de capital |
| **Order Manager** | Executa entrada, SL, TP de forma atomizada | Sem duplicação, sem perdas |
| **Storage Layer** | Registra sinais, ordens, resultados em MongoDB | Auditoria e análise histórica |
| **Logger** | Estrutura de logging (JSON em prod, console em dev) | Rastreabilidade e debugging |
| **Exchange Integration** | Comunicação assíncrona com Binance via ccxt | Confiabilidade e resiliência |

---

## 🤔 PORQUÊ — Justificativa e Contexto

### Problema que Resolve

| Problema | Como Phicube Resolve |
|---|---|
| **Emocionalidade em decisões** | Regras sistemáticas, sem exceções — máquina executa |
| **Inconsistência operacional** | Mesmo método aplicado a todos os sinais, 24/7 |
| **Falta de histórico auditável** | Cada operação registrada com contexto completo |
| **Risco descontrolado** | Stop loss obrigatório em toda operação; SL calculado matematicamente |
| **Dificuldade de validação** | Backtests e Testnet para confirmar antes de produção |
| **Credenciais expostas** | Variáveis de ambiente, secrets manager, nunca em código |

### Alinhamento com Manifesto

Este PRD é a **tradução executável** dos 7 princípios do manifesto:

1. ✅ **Disciplina** → Regras hard-coded, sem exceções
2. ✅ **Gestão de risco** → Stop loss obrigatório; fórmula de posição baseada em risco
3. ✅ **Transparência** → Logs JSON, MongoDB audit trail
4. ✅ **Configurabilidade** → Símbolos, timeframes, % risco definidos via config
5. ✅ **Segurança** → API Keys em .env, não em código
6. ✅ **Resiliência** → Retry logic, reconexão, prevenção de duplicação
7. ✅ **Evolução orientada por dados** → Métricas de performance armazenadas

---

## � PARA QUEM — Persona

### Operador / Dono do Sistema

- **Perfil:** Conhece a estratégia BO Williams Phicube e opera ativamente
- **Necessidade:** Automatizar a execução do próprio método com disciplina total — sem emoção, sem erro humano de execução
- **Sucesso:** O bot executa cada sinal exatamente como o método define; histórico auditável para revisão própria de performance
- **Preocupações:**
  - "O bot está seguindo as regras exatas do Phicube?"
  - "Meu capital está protegido por stop loss em toda operação?"
  - "Consigo auditar o que aconteceu em cada trade?"
  - "Minhas credenciais estão seguras?"

---

## 🎯 Objetivos Estratégicos

### OKR Nível 1 — Visão (12 meses)

**Objetivo:** Operar o método Phicube com disciplina total e confiabilidade comprovada
**Key Results:**

- [ ] 1000+ horas de operação contínua validadas em produção sem intervenção manual
- [ ] 0 casos de fuga de credencial ou operação não autorizada
- [ ] 0 operações divergentes das regras do método (auditadas via log)
- [ ] Histórico de performance pessoal completo e consultável

### OKR Nível 2 — Escopo MVP (3-6 meses)

**Objetivo:** Lançar MVP robusto com core funcional
**Key Results:**

- [ ] Signal Engine acurado (validado contra histórico 200+ candles)
- [ ] Risk Manager preciso (testes com 50+ cenários de posição)
- [ ] Order Manager executando sem falhas em Testnet (100% success rate)
- [ ] 80%+ cobertura de testes unitários
- [ ] Documentação operacional completa
- [ ] Docker build produção-ready

### OKR Nível 3 — Trimestral (Meta atual)

**Objetivo:** Consolidar infraestrutura + validar estratégia
**Key Results:**

- [ ] ccxt + Motor async rodando sem memory leaks
- [ ] Alligator + AO + Fractais implementados e testados (vs. teoria)
- [ ] MongoDB indexes otimizados para queries rápidas
- [ ] Testnet rodando 48h contínuas sem crash
- [ ] Relatórios de performance automáticos

---

## 📊 Escopo Detalhado

### ✅ MVP — Fase 1 (Mínimo Viável)

#### Funcionalidades Críticas

1. **Detecção de Sinal**
   - Input: Histórico OHLCV (Open, High, Low, Close, Volume) em qualquer timeframe
   - Processamento: Alligator (SMMA), Awesome Oscillator, Fractais 5-barra
   - Output: `Signal(symbol, timeframe, direction, entry, SL, TP, fractal_ref)`
   - Critério de sucesso: Validação manual contra 20+ setups históricos

2. **Cálculo de Posição**
   - Input: `Signal`, saldo disponível, `risk_per_trade_pct`
   - Processamento: `qty = (balance * risk%) / stop_distance`
     - **`balance` = campo `free` retornado pelo ccxt** (saldo livre de margem — exclui margem em uso e reservas)
   - Limite: Nunca exceder `max_capital_allocation_pct` por símbolo
     - **Violação → bloquear a operação + emitir log WARN** (nunca silencioso, nunca executar parcialmente)
   - Limite: Nunca ter mais de `max_open_positions` simultâneas
   - Output: `PositionSize(quantity, risk, reward, RRR)`
   - Critério de sucesso: Testes com 50 cenários; 0 violações de limite

3. **Execução de Ordem**
   - Input: `PositionSize`
   - Processamento:
     - Set leverage + margin mode
     - Market order entrada
     - Stop loss order (STOP_MARKET, reduceOnly)
     - Take profit order (TAKE_PROFIT_MARKET, reduceOnly)
   - Rollback: Se qualquer ordem falha, cancel tudo e reportar
   - Output: `Trade(entry_id, SL_id, TP_id, status, entry_price, ...)`
   - Critério de sucesso: 100% success rate em 50 execuções Testnet

4. **Monitoramento e Logging**
   - Event: Cada sinal detectado → log JSON
   - Event: Cada ordem executada → log + MongoDB trade record
   - Event: Cada erro → log estruturado + alerta
   - Retenção: Mínimo 90 dias de histórico
   - Criterio de sucesso: Zero operações sem log; trace-back completo

5. **Resiliência**
   - Reconexão: Se Binance cai, retry 3x com backoff exponencial
   - Durabilidade: Nenhuma ordem duplicada se bot reinicia
   - Health check: Testnet + bot health endpoint respondendo
   - Critério de sucesso: Testnet 48h contínuas sem falha

6. **Notificação ao Operador** *(RF-10)*
   - Canal: Telegram (bot token + chat_id configurados via `.env`)
   - Opcional: se `TELEGRAM_TOKEN` não configurado, bot opera normalmente sem notificação
   - Implementação: chamada HTTP POST via `aiohttp` (dependência já presente no projeto)
   - Eventos notificados:
     - **Trade aberto** — símbolo, direção, entry, SL, TP, quantidade
     - **Trade fechado** — símbolo, resultado em USDT, RRR realizado
     - **Erro crítico** — descrição do erro + timestamp
     - **SL não executado após entrada** — alerta de intervenção manual necessária
   - Fora de escopo: notificação de sinal detectado, logs de debug, reconexão
   - Critério de sucesso: os 4 eventos chegam ao Telegram em Testnet; ausência de token não quebra o bot

7. **Relatório de Performance** *(RF-11)*
   - Escopo MVP: dados disponíveis para consulta manual — não dashboard, não automático
   - **Contrato de dado obrigatório no Storage** (pré-requisito do relatório):

     | Campo | Tipo | Descrição |
     |---|---|---|
     | `exit_price` | `float` | Preço de fechamento do trade |
     | `closed_at` | `datetime` | Timestamp de fechamento |
     | `pnl_usdt` | `float` | P&L realizado em USDT |
     | `close_reason` | `str` | `SL` / `TP` / `manual` |

   - Métricas calculadas com esses dados: total de trades, win rate (%), P&L acumulado USDT, RRR médio realizado
   - Critério de sucesso: após 10 trades em Testnet, todos os campos acima estão gravados e as métricas são calculáveis

#### Configuração (User-facing)

```ini
# .env
BINANCE_API_KEY=xxx
BINANCE_API_SECRET=yyy
BINANCE_TESTNET=true  # true=Testnet, false=Produção

SYMBOLS=BTCUSDT,ETHUSDT  # CSV
TIMEFRAMES=4h,1d         # CSV
RISK_PER_TRADE_PCT=1.0   # 1% por operação
RISK_REWARD_RATIO=2.0    # TP = entry + (entry - SL) * RRR
LEVERAGE=5               # Para Futures (máximo aceito: 20x)
MAX_CAPITAL_ALLOCATION_PCT=30  # Max 30% do saldo em 1 símbolo
MAX_OPEN_POSITIONS=3     # Máximo 3 trades abertos
LOG_LEVEL=INFO

# Notificação Telegram (opcional — bot opera normalmente se não configurado)
TELEGRAM_TOKEN=           # Token do bot Telegram
TELEGRAM_CHAT_ID=         # Chat ID do operador
```

### ⏭️ Fase 2 (Expansão)

- Relatório automático periódico de performance via Telegram (extensão do RF-10/RF-11)
- Dashboard de performance em tempo real
- Backtests e walk-forward analysis
- Ajuste automático de parâmetros baseado em performance
- Análise de performance por símbolo e timeframe
- Múltiplas estratégias
- Suporte a mais timeframes (1m, 5m, 15m, etc.)

### ❌ Out of Scope (v1)

- Operar em corretoras além da Binance
- Recomendação de investimento
- Garantia de lucro
- Dashboard web full-featured
- Histórico gráfico (charting)

---

## 📏 Critérios de Sucesso

### Funcionais

| Critério | Métrica | Alvo |
|---|---|---|
| Acurácia do Sinal | % sinais validados vs. histórico | ≥ 95% |
| Execução sem falha | % ordens executadas com sucesso em Testnet | ≥ 99% |
| Resiliência | Horas contínuas sem crash | ≥ 48h |
| Cobertura de testes | % linhas de código testadas | ≥ 80% |
| Traçabilidade | Toda operação com log completo | 100% |

### Não-Funcionais

| Critério | Métrica | Alvo |
|---|---|---|
| Latência | Tempo entre sinal e execução | ≤ 2 segundos |
| Escalabilidade | Símbolos simultâneos | ≥ 20 |
| Segurança | Fuga de chave de API | 0 casos |
| Documentação | Cobertura de código + operação | 100% |
| Compliance | Auditabilidade de operações | 100% |

---

## 🏗️ Requisitos Técnicos

### Stack Necessário

- **Linguagem:** Python 3.11+
- **Async:** asyncio (não threads)
- **Exchange:** ccxt (async binanceusdm)
- **Database:** MongoDB 7+ (motor para async)
- **Observabilidade:** structlog (JSON logging)
- **Container:** Docker + Docker Compose
- **Testes:** pytest + pytest-asyncio + pytest-mock
- **CI/CD:** GitHub Actions (futura)

### Dependências Críticas

| Lib | Razão | Versão Min |
|---|---|---|
| ccxt | Comunicação Binance async | 4.0+ |
| motor | MongoDB async driver | 3.0+ |
| pydantic | Config validation | 2.0+ |
| structlog | Logging estruturado | 24.1+ |
| aiohttp | HTTP async (fallback) | 3.9+ |
| asyncio-throttle | Rate limiting para API | latest |

### Restrições de Segurança

- [ ] **Nunca** colocar chaves em .py ou .md
- [ ] **Sempre** usar variáveis de ambiente via `.env` (git-ignored)
- [ ] **Logs** não devem conter chaves, mesmo ofuscadas
- [ ] **Container** roda com user não-root
- [ ] **MongoDB** requer autenticação em produção
- [ ] **Dockerfile** multi-stage: builder → runtime
- [ ] **`LEVERAGE` máximo aceito = 20x** — o bot deve rejeitar na inicialização qualquer valor acima desse limite; não é negociável por configuração

---

## 📅 Roadmap (Planejamento de Alto Nível)

### Sprint 1-2 (Semanas 1-4) — Core Engine

- Signal Engine (Alligator + AO + Fractals)
- Risk Manager (Position Sizing)
- Order Manager (Execução básica)
- Testes unitários (≥ 70% coverage)

### Sprint 3-4 (Semanas 5-8) — Integração

- ccxt + Motor integrados
- MongoDB storage + indexação
- Testnet execução end-to-end
- Testes de integração

### Sprint 5-6 (Semanas 9-12) — Hardening

- Resiliência (retry, reconexão)
- Segurança (secrets management)
- Observabilidade (logging estruturado)
- Documentação operacional
- **MVP Release em Testnet**

### Sprint 7+ (Fase 2) — Expansão

- Dashboard
- Backtests
- Mais estratégias / timeframes

---

## 🎬 Como Este Documento é Usado

### Para **Engenheiros**

- Use escopo e requisitos técnicos como spec de implementação
- **As regras exatas de entrada, saída, cálculo de SL/TP e contratos de interface estão em [`docs/SDD/SPEC.md`](docs/SDD/SPEC.md) — essa é a fonte de verdade técnica; o PRD define o *quê*, a SPEC define o *como***
- Valide cada feature contra critérios de sucesso
- Use roadmap para priorização
- Ative skills de validação (@signal-review, @qa-review, @security-audit) ao implementar

### Para **Time A (Refinamento)**

- Novo tema de sessão? Valide se está em escopo deste PRD
- Se novo requisito, produz artefatos que atualizam este PRD
- PRD reflete apenas a visão do operador/dono — sem escopo de multi-usuário

### Para **Time B (Execução)**

- Artefatos do Time A devem referenciar este PRD
- Se há novo requisito, valide se está alinhado com PRD
- PRD é a "fonte de verdade" — bloqueie fora de escopo

---

## 📞 Governance

### Proprietários

- **Product Vision:** Trader Sênior + Product Owner
- **Requisitos Técnicos:** Backend Sênior + Quant Developer
- **Segurança:** AppSec
- **Operação:** DevOps + QA Engineer

### Decisões de Escopo

- **Dentro de scope:** Time B executa
- **Fora de scope:** Time A debate em próxima sessão
- **Urgente:** Escalar para humano (você)

### Atualização do PRD

- **Trimestral:** Revisão completa com Time A + Time B
- **Ad-hoc:** Se decisão do Time A impacta PRD, atualizar antes de Time B executar
- **Versionamento:** Incrementar versão; guardar histórico

---

## 🚨 Riscos Conhecidos e Mitigações

| Risco | Impacto | Mitigação |
|---|---|---|
| Fuga de API Key | Crítico — perda de capital | Secrets manager, variáveis de ambiente, nunca em logs |
| Operação duplicada (crash + restart) | Alto — operações múltiplas | ID único por operação, transação atômica |
| Stop Loss não executa | Alto — perda maior que esperado | SL order imediato após entry; monitoramento contínuo |
| Indicadores descalibrados | Médio — sinais falsos | Validação contra 200+ candles históricos; backtests |
| Binance API rate limit | Médio — rejeição de ordens | Throttle assíncrono; retry com backoff |
| MongoDB indisponível | Médio — perda de auditoria | Logging local + sync posterior; health check |

---

## ✍️ Histórico de Versões

| Versão | Data | Autor | Mudanças |
|---|---|---|---|
| 1.0 | 2026-05-01 | Time A | Documento inicial baseado em Manifesto |

---

**Este PRD é um documento vivo. Feedback e refinamentos são bem-vindos. Toda decisão importante deve retornar aqui para validação.**
