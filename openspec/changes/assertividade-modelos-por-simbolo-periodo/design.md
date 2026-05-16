## Context

O dashboard atual já expõe métricas de performance consolidadas e tabelas operacionais, porém não entrega uma leitura gerencial direta de assertividade por símbolo e por janela temporal selecionável. A demanda é permitir diagnóstico rápido de qualidade dos modelos para decisões de continuidade, ajuste de risco e priorização de pares.

Restrições e contexto técnico:
- O frontend canônico é servido em `:8080` pelo `dashboard-api`.
- A API já possui endpoints de performance e histórico de trades/sinais.
- Devemos reutilizar o núcleo de cálculo de métricas existente para evitar divergência matemática.

## Goals / Non-Goals

**Goals:**
- Disponibilizar consulta de assertividade por símbolo/período com filtros explícitos.
- Expor métricas gerenciais consistentes: assertividade, sinais, trades, conversão sinal->trade, PnL, profit factor, drawdown.
- Expor ranking por símbolo e evolução temporal no período.
- Manter compatibilidade com contratos atuais e reutilizar o core de métricas.

**Non-Goals:**
- Não alterar lógica de geração de sinal/execução de ordens.
- Não introduzir autenticação nova neste escopo.
- Não implementar, nesta fase, visualização gráfica avançada externa (bibliotecas de charting).

## Decisions

1. **Reuso do core de métricas existente**
   - Decisão: usar a base de `performance-metrics-unification` para cálculos de win-rate/PnL/PF/drawdown.
   - Racional: evita drift entre visões de performance e assertividade.
   - Alternativa considerada: cálculo paralelo dedicado para dashboard (rejeitada por risco de divergência).

2. **Strategy Pattern para seleção de período**
   - Decisão: modelar filtros de período com `Strategy` (`7d`, `30d`, `90d`, `custom`) em vez de condicionais espalhadas.
   - Racional: atende uso rápido gerencial e investigação detalhada.
   - Alternativa: `if/else` central com branches fixas (rejeitada por baixa extensibilidade).

3. **Facade para endpoint de assertividade**
   - Decisão: criar um serviço/facade de aplicação para orquestrar consulta de sinais/trades, agregação e montagem de resposta.
   - Racional: reduz acoplamento entre rota FastAPI e detalhes de cálculo/persistência.
   - Alternativa: concentrar toda lógica na rota (rejeitada por baixa testabilidade).

4. **Série temporal em tabela na fase inicial**
   - Decisão: retornar série temporal por bucket (dia/semana) e renderizar tabela inicialmente.
   - Racional: menor acoplamento, validação rápida e sem dependência extra de frontend.
   - Alternativa: gráfico imediato com biblioteca externa (postergada).

5. **Adapter/DTO para contrato estável de resposta**
   - Decisão: mapear entidades internas para DTOs específicos de assertividade (resumo, ranking, série) via adapter.
   - Racional: evita vazamento de estrutura interna e estabiliza contrato para frontend.
   - Alternativa: retorno direto de documentos do repositório (rejeitada por fragilidade de contrato).

6. **Repository como fronteira de dados**
   - Decisão: manter consultas/extrações em camada de repositório, com interface clara para o facade.
   - Racional: preserva isolamento da regra de negócio e facilita testes com stubs/fakes.
   - Alternativa: queries diretas na camada de rota/serviço de UI (rejeitada por acoplamento).

7. **Novo contrato de endpoint dedicado de assertividade**
   - Decisão: endpoint dedicado para assertividade no dashboard API, separado dos endpoints globais de performance.
   - Racional: clareza de contrato e evolução independente.
   - Alternativa: expandir endpoint atual de performance com múltiplos modos (rejeitada por complexidade e ambiguidade).

## Risks / Trade-offs

- [Risco] Custo de agregação em janelas longas com muitos símbolos -> Mitigação: limitar página/resultado, índices adequados e agregação incremental.
- [Risco] Divergência semântica entre “sinal” e “trade executado” -> Mitigação: contrato explícito para taxa de conversão e cenários de teste.
- [Risco] Inconsistência temporal (timezone) -> Mitigação: normalizar entrada em UTC e manter convenção de exibição já adotada no frontend.
- [Trade-off] Entrega inicial em tabela para evolução temporal reduz apelo visual -> ganho de previsibilidade e menor risco técnico.

## Migration Plan

1. Implementar endpoint backend de assertividade com filtros por período/símbolo/timeframe.
2. Implementar agregações por símbolo e série temporal reutilizando core de métricas.
3. Integrar frontend canônico (`:8080`) com novos filtros e seções.
4. Adicionar testes focados de API, cálculo e frontend.
5. Validar com `openspec validate --strict` e gates de testes/lint.

Rollback:
- Remover registro das novas rotas do dashboard-api.
- Reverter seção de UI de assertividade no frontend.
- Manter endpoints atuais de performance sem alteração comportamental.

## Open Questions

- Granularidade padrão da série temporal para períodos >30d: diário ou semanal?
- Ordenação padrão do ranking por símbolo: assertividade ou PnL?
- Necessidade de paginação no ranking já na primeira versão?
