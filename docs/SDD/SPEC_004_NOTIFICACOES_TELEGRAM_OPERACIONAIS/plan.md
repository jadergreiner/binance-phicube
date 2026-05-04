# Plan — SPEC_004: Notificações Operacionais via Telegram

**spec_id:** SPEC_004
**status:** Revisado — pronto para tasks
**data:** 2026-05-02
**autor:** Time A (Refinamento)

---

## Rastreabilidade

```text
MANIFESTO.md
  └─ Princípio 2 (Gestão de risco) -> alerta rápido em falha de proteção
  └─ Princípio 3 (Transparência) -> notificação explícita de eventos críticos
        ↓
PRD.md — Funcionalidades Críticas (RF-10)
  └─ trade aberto, trade fechado, erro crítico, SL não executado
        ↓
docs/SDD/SPEC.md — contratos de OrderManager e logging
        ↓
SPEC_004 — canal Telegram opcional e resiliente
```

---

## Meta

- **spec_id:** SPEC_004
- **prd_fonte:** `PRD.md` -> Funcionalidades Críticas -> RF-10
- **objetivo:** Implementar notificações Telegram opcionais para eventos operacionais críticos sem impactar continuidade do bot.
- **escopo:** settings opcionais, módulo `notifications`, integração com fluxo de trade, testes e validações de segurança.
- **fora_de_escopo:** relatórios periódicos, canais alternativos, comandos inbound.
- **principios_manifesto_aplicados:** Princípios 2 (Risco), 3 (Transparência), 6 (Resiliência).

---

## Decisões Arquiteturais (Time A — sessão 2026-05-02)

| Decisão | Escolha | Justificativa |
|---|---|---|
| Estratégia sem credenciais Telegram | `NullNotifier` | Evita condicionais espalhadas e mantém fluxo estável |
| Transporte HTTP | `aiohttp.ClientSession` compartilhada | Reuso de conexão e menor overhead |
| Falha de notificação | Retornar `False`, nunca exceção fatal | Invariante de resiliência do bot |
| Ponto de integração | `TradingMonitor` + eventos de `OrderManager` | Menor acoplamento, máxima cobertura dos 4 eventos |
| Formato de mensagem | Texto simples padronizado | Compatibilidade e simplicidade operacional |

---

## Riscos e Mitigações

| risco | impacto | mitigacao |
|---|---|---|
| API Telegram indisponível | medio | Retry curto + log de falha, sem parar bot |
| Vazamento de segredo em log | alto | Sanitização + testes específicos |
| Excesso de mensagens em erro recorrente | medio | Deduplicação básica por ciclo/tick |
| Ambiguidade no evento "trade fechado" | medio | Definir contrato explícito no `TradeStatus` e origem do fechamento |

---

## Estratégia de Execução

1. **Fase 1 - Configuração:** ampliar `Settings` e `.env.example` com `TELEGRAM_TOKEN` e `TELEGRAM_CHAT_ID` opcionais.
2. **Fase 2 - Infraestrutura:** criar módulo `src/notifications/` com contratos `NotificationEvent`, `Notifier`, `TelegramNotifier`, `NullNotifier`.
3. **Fase 3 - Integração de eventos:** conectar envio nos eventos de trade aberto, falha crítica e SL não protegido; preparar gancho para trade fechado.
4. **Fase 4 - Testes:** validar fallback sem Telegram, falhas de rede, payload e ausência de vazamento.
5. **Fase 5 - Validação final:** QA e security-audit com evidências.

---

## Dependências

- `aiohttp` já presente no projeto (confirmar versão no ambiente).
- Estrutura atual de eventos em `src/main.py` e `src/trading/order_manager.py`.
- Testes existentes de configuração e trading para extensão.

---

## Critérios de Pronto do Plano

- [ ] Plano rastreável para a SPEC_004
- [ ] Dependências mapeadas
- [ ] Riscos com mitigação
- [ ] Pronto para gerar/usar `tasks.json`
