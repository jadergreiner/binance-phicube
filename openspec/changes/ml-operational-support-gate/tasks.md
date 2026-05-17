## Tasks

- [x] 1.1 Criar estrutura da camada ML auxiliar (servico/stub) desacoplada do fluxo de execucao real
- [x] 1.2 Integrar chamada da camada ML no ponto pos-avaliacao do BO em shadow mode
- [x] 1.3 Garantir fallback seguro: erro/timeout de ML nao interrompe ciclo e nao altera decisao BO

- [x] 2.1 Adicionar configuracoes/feature flags globais (`ml_support_enabled`, `ml_support_shadow_mode`)
- [x] 2.2 Adicionar filtro canario por simbolo/timeframe (`ml_support_symbol_timeframes`)
- [x] 2.3 Implementar caminho de disable imediato mantendo BO puro

- [x] 3.1 Estender payload de diagnostico de ciclo com campos ML (`ml_enabled`, `ml_shadow_mode`, `ml_score`, `ml_decision`, `ml_reason`, `ml_model_version`)
- [x] 3.2 Persistir campos ML na trilha de auditoria com retrocompatibilidade para legados
- [x] 3.3 Expor campos ML nos endpoints de diagnostico sem quebrar contrato atual

- [x] 4.1 Adicionar testes de contrato API para presenca/ausencia (legado) dos campos ML
- [x] 4.2 Adicionar testes de comportamento para shadow mode sem impacto operacional
- [x] 4.3 Adicionar testes de falha segura (erro de inferencia -> BO continua)

- [x] 5.1 Adicionar metricas de observabilidade da camada ML (contagem, score, decisao, latencia, falha)
- [x] 5.2 Adicionar logs estruturados para correlacao BO vs ML por ciclo
- [x] 5.3 Validar que dashboards/diagnosticos conseguem comparar baseline BO vs apoio ML

- [x] 6.1 Definir e documentar baseline operacional (BO puro) para janela de avaliacao
- [x] 6.2 Implementar relatorio comparativo para criterios Go/No-Go (expectancy, drawdown, latencia, disponibilidade)
- [x] 6.3 Registrar decisao de promocao: manter shadow ou habilitar proxima fase

- [x] 7.1 Rodar validacoes finais (lint, testes focados, openspec validate --strict)
- [ ] 7.2 Atualizar changelog da change com riscos conhecidos e plano de rollback
- [ ] 7.3 Preparar handoff para fase de apply sem alterar execucao real nesta etapa
