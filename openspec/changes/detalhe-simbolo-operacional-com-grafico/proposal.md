# Change Proposal: detalhe-simbolo-operacional-com-grafico

## Contexto

O dashboard atual não oferece uma visão completa por símbolo para tomada de decisão operacional e escalabilidade de capital.

## Problema

A leitura operacional está fragmentada:

- Home não consolida claramente o estado por símbolo.
- Página de detalhe não possui gráfico com zonas de observação e justificativa.
- Última análise não está padronizada em linguagem humana simples.

## Objetivo

Consolidar a especificação da página de detalhe por símbolo com:

1. Blocos operacionais padronizados.
2. Gráfico operacional com regiões de preço observáveis.
3. Contratos de dados explícitos por bloco.
4. Explicação da última análise em linguagem humana simples.

## Escopo

- Definir UX e IA da Home (lista de símbolos) e do Detalhe (raio-x por símbolo).
- Definir contrato de dados do bloco de gráfico operacional.
- Definir contrato de dados de explicação humana (`human_explanation`).
- Definir estados de UI e critérios de aceite.
- Definir MVP por prioridade (P0/P1) para evitar escopo elástico.
- Definir semáforo de risco operacional por símbolo (`ok`, `atencao`, `bloqueado`).
- Definir taxonomia mínima de zonas de preço (`entrada`, `invalidação`, `alvo`, `observacao`).
- Definir padrão de consistência temporal e numérica por bloco (unidade, precisão, timestamp).

## Fora de Escopo

- Implementação frontend/backend.
- Alterações de estratégia de sinal.
- Alterações de risco/execução de ordens.

## Especificações Mínimas Obrigatórias (Time A)

### 1) Recorte de MVP

- **P0**: Home com todos os símbolos + detalhe com blocos obrigatórios:
  - `snapshot`
  - `ultima_analise_humana`
  - `grafico_operacional_com_zonas`
  - `historico_trades`
- **P1**: refinamentos visuais, filtros avançados e expansões de métricas.

### 2) Zonas Operacionais no Gráfico

Cada zona deve possuir tipo e ação esperada:

- `entrada`
- `invalidação`
- `alvo`
- `observacao`

Toda zona deve conter explicação curta em linguagem humana:

- `o_que_e`
- `por_que_importa`
- `o_que_fazer`

### 3) Semáforo de Risco Operacional por Símbolo

Estado obrigatório por símbolo:

- `ok`
- `atencao`
- `bloqueado`

A proposta deve incluir gatilhos mínimos de bloqueio para escalabilidade de capital
(ex.: inconsistência de dados, eventos de execução rejeitada, dado desatualizado).

### 4) Consistência Temporal e Numérica

Todos os blocos devem explicitar:

- unidade (`USDT`, `%`, preço)
- precisão esperada por valor
- `timestamp` de referência (`as_of` em UTC)
- coerência de `symbol` + `timeframe` entre blocos

### 5) Explicação Humana Padronizada

Contrato textual obrigatório:

- `what_i_saw`
- `what_i_decided`
- `why`
- `next_step`
- `full_text`

Regras:

- sem jargão técnico
- frases curtas
- até 4 frases no resumo

## Valor Esperado

- Maior clareza operacional por símbolo.
- Redução de ambiguidade na interpretação da última análise.
- Base técnica pronta para implementação incremental com baixo retrabalho.
- Segurança adicional para decisão de escala de capital por símbolo.

## Critérios de Sucesso do Proposal

- Proposal define claramente P0/P1.
- Proposal contém semáforo de risco operacional.
- Proposal estabelece taxonomia mínima de zonas de preço.
- Proposal explicita consistência temporal/numérica.
- Proposal define padrão obrigatório de explicação humana.
