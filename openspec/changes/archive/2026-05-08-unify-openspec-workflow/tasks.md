## 1. Governanca do fluxo OpenSpec

- [x] 1.1 Definir formalmente no repositório que o CLI oficial `openspec` é o fluxo canônico
- [x] 1.2 Documentar a depreciação do fluxo compat local e a data de corte

## 2. Alinhamento de documentação e CLI operacional

- [x] 2.1 Atualizar `README.md` para remover instruções do fluxo compat local como padrão
- [x] 2.2 Atualizar `AGENTS.md` (ou doc de governança equivalente) com regra única OpenSpec
- [x] 2.3 Ajustar `tools/phicube_ops_cli.py` para não promover `openspec-local` como caminho principal

## 3. Transicao de mudanças em andamento

- [x] 3.1 Definir checklist de migração para changes iniciadas no fluxo local compat
- [x] 3.2 Aplicar checklist na change ativa `ajuste-risco-intraday` (ou registrar exceção explícita)

## 4. Validacao e fechamento

- [x] 4.1 Executar `openspec validate --strict` na change `unify-openspec-workflow`
- [x] 4.2 Revisar consistência final (proposal/design/spec/tasks) e preparar para `/opsx:apply`
