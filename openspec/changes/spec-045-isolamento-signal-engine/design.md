## Context

O fluxo atual do bot avalia sinais dentro da orquestração de runtime, com acoplamento entre obtenção de dados, avaliação de estratégia e tratamento operacional. Isso dificulta testes unitários estritos do comportamento de sinal e aumenta risco de regressão ao alterar regras de entrada/saída. A mudança precisa preservar o comportamento de trading atual, manter compatibilidade com os contratos internos já usados no loop principal e não introduzir dependências externas novas.

## Goals / Non-Goals

**Goals:**
- Isolar o `SignalEngine` por meio de um contrato explícito de entrada e saída.
- Separar responsabilidades entre cálculo de sinal (domínio) e orquestração (runtime).
- Padronizar tratamento de erro e observabilidade na borda de chamada do engine.
- Permitir testes unitários determinísticos do engine e do adaptador sem exchange/mongo.

**Non-Goals:**
- Redesenhar a estratégia BO Williams ou alterar regras de negócio de sinal.
- Alterar API pública do dashboard.
- Introduzir framework de DI ou novos serviços externos.

## Decisions

1. **Criar contrato explícito com DTOs imutáveis para entrada/saída de sinal**
   - Decisão: definir estruturas dedicadas (ex.: `SignalInput`, `SignalDecision`) com campos mínimos necessários para avaliação.
   - Racional: reduz dependência implícita de estruturas do runtime e melhora testabilidade.
   - Alternativas consideradas:
     - Reutilizar dicionários soltos: rejeitado por baixa rastreabilidade e maior risco de quebra silenciosa.
     - Acoplar direto ao modelo de trade: rejeitado por misturar domínio de sinal com execução.

2. **Introduzir adaptador de avaliação entre orquestrador e `SignalEngine`**
   - Decisão: encapsular a chamada ao engine em um adaptador único responsável por validação leve, captura de exceções e normalização de retorno.
   - Racional: centraliza políticas de chamada e evita replicação de lógica em múltiplos pontos do loop.
   - Alternativas consideradas:
     - Chamada direta em `main.py`: rejeitado por manter acoplamento e duplicar tratamento operacional.

3. **Manter compatibilidade comportamental via mapeamento estável de decisão**
   - Decisão: preservar semântica atual de `LONG`/`SHORT`/`None` no boundary, com conversão explícita entre tipos internos e externos.
   - Racional: evita mudanças colaterais em risco/ordem/notificação.
   - Alternativas consideradas:
     - Alterar enumeração/contrato em cadeia completa: rejeitado por ampliar escopo e risco.

4. **Cobertura de testes em duas camadas**
   - Decisão: testes unitários do `SignalEngine` (regra) + testes do adaptador (contrato/erros/log).
   - Racional: acelera feedback em CI e delimita origem de regressões.
   - Alternativas consideradas:
     - Apenas testes de integração: rejeitado por flakiness e diagnóstico lento.

## Risks / Trade-offs

- **[Risco] Divergência entre contrato novo e uso legado no runtime** → **Mitigação:** adicionar testes de contrato e validação de mapeamento no adaptador.
- **[Risco] Sobrecarga de manutenção por mais uma camada** → **Mitigação:** manter adaptador enxuto e com responsabilidade única.
- **[Risco] Logs inconsistentes durante transição** → **Mitigação:** padronizar chaves de evento e preservar nomes já consumidos por monitoramento.

## Migration Plan

1. Criar tipos de contrato e adaptador isolado em `src/strategy/`.
2. Integrar adaptador no ponto atual de avaliação de sinal do orquestrador.
3. Manter caminho legado temporário atrás de fallback interno (somente durante refatoração).
4. Adicionar/ajustar testes unitários e integração focados no boundary.
5. Remover fallback legado após validação dos testes e lint.
6. Rollback: reverter integração do adaptador para chamada anterior mantendo `SignalEngine` intacto.

## Open Questions

- O contrato de entrada deve carregar metadados operacionais (ex.: símbolo/timeframe) ou apenas séries já normalizadas?
- O adaptador deve expor motivo estruturado para decisão `None` (sem sinal) já nesta change ou em evolução posterior?
- Há necessidade de métricas dedicadas por causa de não-sinal além dos logs atuais?
