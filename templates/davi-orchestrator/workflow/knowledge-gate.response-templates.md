# Knowledge Gate Response Templates

Operational response templates for Davi after the mandatory Knowledge Gate.

## Template A: Adherent

Use when:

- Knowledge exists and proposal is adherent to current rules/architecture/governance.

```text
Intencao capturada:
[Resumo objetivo em 1-2 linhas]

Knowledge Gate:
YES - Adherente

Caminho decidido:
[Q&A | RCA | Nova Implementacao]

Analise de aderencia:
- Regras aderentes: [...]
- Arquitetura aderente: [...]
- Governanca aderente: [...]

Proxima acao:
[Descrever o proximo passo operacional]

Gate humano:
[Nao aplicavel agora | Solicitacao de aprovacao desta etapa]
```

Example:

```text
Intencao capturada:
Validar proposta de ajuste no launcher deterministico.

Knowledge Gate:
YES - Adherente

Caminho decidido:
Nova Implementacao

Analise de aderencia:
- Regras aderentes: limites operacionais existentes cobrem a proposta.
- Arquitetura aderente: sem mudanca de modulo critico.
- Governanca aderente: sem novo controle obrigatorio.

Proxima acao:
Iniciar SDD etapa 1 e preparar etapa 2 padronizada para aprovacao.

Gate humano:
Aprova iniciar a etapa 1 do SDD?
```

## Template B: Divergent

Use when:

- Knowledge exists but proposal diverges from current rules/architecture/governance.

```text
Intencao capturada:
[Resumo objetivo em 1-2 linhas]

Knowledge Gate:
YES - Divergente

Divergencias detectadas:
- Regras: [...]
- Arquitetura: [...]
- Governanca: [...]

Bloqueio:
Avanco bloqueado ate decisao formal do humano.

Opcoes para decisao humana:
1) Evoluir regras/conhecimento para acomodar a proposta
2) Ajustar a proposta para aderir ao conhecimento atual

Pergunta de decisao:
Qual opcao voce aprova (1 ou 2)?
```

Example:

```text
Intencao capturada:
Adicionar comportamento RL fora das restricoes atuais.

Knowledge Gate:
YES - Divergente

Divergencias detectadas:
- Regras: politica atual nao permite este comportamento.
- Arquitetura: fluxo atual nao suporta este modo sem ajuste de pipeline.
- Governanca: faltam controles para o novo risco operacional.

Bloqueio:
Avanco bloqueado ate decisao formal do humano.

Opcoes para decisao humana:
1) Evoluir regras/conhecimento para acomodar a proposta
2) Ajustar a proposta para aderir ao conhecimento atual

Pergunta de decisao:
Qual opcao voce aprova (1 ou 2)?
```

## Template C: No Knowledge

Use when:

- No current knowledge exists about the topic.

```text
Intencao capturada:
[Resumo objetivo em 1-2 linhas]

Knowledge Gate:
NO - Sem conhecimento previo suficiente

Decisao de orquestracao:
Acionar Refinadores para construir baseline de conhecimento.

Pergunta obrigatoria ao humano:
Aprova promover o conhecimento capturado para os shared packs do Davi?

Plano imediato:
1) Business: definir contexto, regras e escopo
2) Architecture: traduzir em desenho tecnico inicial
3) Governance: definir controles e rastreabilidade
4) Persistir artefatos e submeter aprovacao por etapa

Proxima acao:
Iniciar SDD etapa 1 (alto nivel) com perguntas objetivas ao humano.

Gate humano:
Aprova iniciar construcao de conhecimento pela camada Business?
```

Example:

```text
Intencao capturada:
Avaliar nova demanda sem historico registrado.

Knowledge Gate:
NO - Sem conhecimento previo suficiente

Decisao de orquestracao:
Acionar Refinadores para construir baseline de conhecimento.

Plano imediato:
1) Business
2) Architecture
3) Governance
4) Persistencia + aprovacoes formais

Proxima acao:
Iniciar etapa 1 do SDD para documentar contexto e objetivo.

Gate humano:
Aprova iniciar a etapa 1 agora?
```

## Usage Rules

- Always run Knowledge Gate before selecting path.
- Always use one of these templates as first operational response.
- Divergent case always blocks progression pending human decision.
- RCA/New Implementation still follow SDD approvals and persisted artifacts.
