# Launcher-Based Pack Boundaries (Project Template)

Project launcher split:

- `INICIAR.BAT` (deterministic)
- `INICIAR_RL.BAT` (reinforcement learning)

## Pack Matrix (MVP)

1. `business.iniciar`
2. `business.iniciar_rl`
3. `architecture.iniciar`
4. `architecture.iniciar_rl`
5. `governance.iniciar`
6. `governance.iniciar_rl`

## Boundaries by Pack

### business.iniciar

Entra:

- Regras de negocio para fluxo deterministico
- Criterios de sucesso do launcher deterministico
- Restrições operacionais de negocio sem RL
Nao entra:
- Politicas de treinamento RL
- Decisoes de arquitetura de modelos

### business.iniciar_rl

Entra:

- Regras de negocio para fluxo RL
- Objetivos de aprendizado e resultados esperados de negocio
- Limites de uso do modo RL
Nao entra:
- Parametros tecnicos de treinamento detalhados
- Controles de compliance/auditoria

### architecture.iniciar

Entra:

- Modulos, interfaces e dependencias do launcher deterministico
- Estrategia tecnica de execucao e validacao
- Decomposicao tecnica de tarefas nao-RL
Nao entra:
- Politicas de risco/compliance
- Hipoteses de negocio

### architecture.iniciar_rl

Entra:

- Arquitetura tecnica do fluxo RL (pipeline, treino, inferencia, fallback)
- Dependencias, limites de desempenho e observabilidade tecnica RL
- Decomposicao tecnica de tarefas RL
Nao entra:
- Metas de negocio sem traducao tecnica
- Decisao final de go/no-go de governanca

### governance.iniciar

Entra:

- Politicas, riscos e controles do launcher deterministico
- Rastreabilidade de decisoes e aprovacoes
- Requisitos de auditoria para o fluxo deterministico
Nao entra:
- Desenho tecnico detalhado
- Definicao de regras de negocio

### governance.iniciar_rl

Entra:

- Politicas, riscos e controles especificos de RL
- Criterios de seguranca operacional para RL
- Rastreabilidade de mudancas de modelos e aprovacoes
Nao entra:
- Ajustes tecnicos de arquitetura de baixo nivel
- Definicoes de objetivo de negocio
