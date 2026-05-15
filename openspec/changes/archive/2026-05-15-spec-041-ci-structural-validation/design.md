## Context

O repositório já possui workflows de qualidade e cobertura, porém sem um gate
estrutural dedicado para validar sincronização de configuração, saúde de
documentação técnica e fronteiras arquiteturais entre camadas. Como resultado,
erros de `.env.example`, drift de SPEC e acoplamentos indevidos podem entrar em
PR sem bloqueio específico.

Restrições e contexto operacional:

- O novo gate precisa complementar, não substituir, os workflows existentes.
- Regras devem ser determinísticas e de baixo custo para execução em PR.
- O desenho deve minimizar falso positivo para não degradar produtividade.
- Segurança exige inspeção de segredos no diff antes do merge.

Stakeholders:

- Engenharia de plataforma/CI (manutenção de pipelines)
- Engenharia de aplicação (consumidores dos erros/warnings)
- Segurança/AppSec (detecção de segredos)
- Documentação técnica (freshness de SPECs)

## Goals / Non-Goals

**Goals:**

- Introduzir workflow de validação estrutural em PR com resultados previsíveis.
- Validar sincronização `.env.example` versus `Settings` com falha bloqueante
  para ausências obrigatórias.
- Detectar SPECs stale com política de severidade por status.
- Validar regras de import entre camadas via análise estática.
- Incluir checagem de segredos no diff como gate adicional de segurança.

**Non-Goals:**

- Substituir workflows de testes, lint e coverage já existentes.
- Implementar testes E2E, benchmark ou deploy automático.
- Resolver arquitetura por refatoração ampla no mesmo change.

## Decisions

### 1) Workflow dedicado `spec041-validation.yml`

Decisão: criar workflow isolado para validação estrutural, acionado em
`pull_request`, com job único e etapas explícitas por validador.

Racional:

- Isolamento facilita troubleshooting e ownership.
- Evita acoplamento com pipelines legadas e reduz risco de regressão.

Alternativas consideradas:

- Incorporar steps em `spec023-validation`: rejeitada por aumentar superfície
  de impacto em pipeline já estabilizada.

### 2) Validadores em scripts Python locais

Decisão: implementar `tools/validate_env_example.py`,
`tools/validate_spec_freshness.py` e `tools/validate_layers.py` como scripts
independentes com códigos de saída claros.

Racional:

- Favorece testabilidade unitária em `tests/tools/`.
- Permite execução local idêntica ao CI para debug rápido.

Alternativas consideradas:

- Regras inline em YAML: rejeitada por baixa testabilidade e manutenção difícil.

### 3) Política de severidade em duas classes

Decisão: separar resultados em `ERROR` (bloqueante) e `WARNING`
(não-bloqueante), com contrato uniforme de saída textual.

Racional:

- Mantém rigor sem travar PR por casos de baixo risco imediato.
- Facilita adoção gradual e calibração de regras.

Alternativas consideradas:

- Tornar todas as regras bloqueantes: rejeitada por alto risco de atrito
  operacional inicial.

### 4) Validação de camadas por AST e mapa configurável

Decisão: extrair imports com AST Python e aplicar regras com mapa declarativo
de dependências permitidas por camada.

Racional:

- AST reduz falsos positivos de parsing textual.
- Mapa declarativo facilita evolução das regras sem reescrever o analisador.

Alternativas consideradas:

- Regex de imports em texto: rejeitada por baixa precisão.

### 5) Segurança de segredos via scanner de diff

Decisão: incluir scanner de segredos no diff de PR como etapa de segurança
complementar.

Racional:

- Reduz chance de vazamento antes do merge.
- Cobertura focada no delta atual, com custo controlado.

Alternativas consideradas:

- Scanner apenas em branch completa: rejeitada por custo maior e ruído.

## Risks / Trade-offs

- [Falso positivo em validação de layer] → Mitigação: regras configuráveis,
  testes com fixtures e allowlist explícita.
- [`.env.example` divergir por campos opcionais] → Mitigação: classificação de
  obrigatórios vs opcionais com políticas distintas de erro/warning.
- [Ruído de SPEC freshness em legado] → Mitigação: severidade por status e
  janela configurável (`--max-age`).
- [Aumento de tempo total de CI] → Mitigação: scripts enxutos, sem dependências
  pesadas e execução paralelizável futura.

## Migration Plan

1. Criar scripts de validação em `tools/` com interfaces de CLI estáveis.
2. Adicionar testes unitários em `tests/tools/` cobrindo cenários nominal/erro.
3. Criar workflow `.github/workflows/spec041-validation.yml` em PR.
4. Rodar em modo estrito para `ERROR` e acompanhar `WARNING` nas primeiras PRs.
5. Ajustar regras/allowlists com base nos primeiros resultados sem quebrar
   contrato de saída.

Rollback:

- Desabilitar temporariamente workflow `spec041-validation.yml` sem impactar
  os demais pipelines.
- Manter scripts versionados para reativação rápida após ajustes.

## Open Questions

- A regra de freshness deve considerar apenas `Data:` de `SPEC.md` ou também
  histórico de commits por arquivo?
- Quais exceções de import entre camadas serão permitidas de forma permanente?
- O scanner de segredos deve operar apenas em `pull_request` ou também em
  `push` para `main`?
