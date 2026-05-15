## ADDED Requirements

### Requirement: Workflow de validação estrutural em PR

O sistema SHALL executar uma pipeline dedicada de validação estrutural em
eventos de `pull_request`, independente dos workflows de qualidade já
existentes.

#### Scenario: Execução automática em pull request

- **WHEN** um pull request for aberto, sincronizado ou reaberto
- **THEN** o workflow de validação estrutural MUST iniciar automaticamente

### Requirement: Sincronização entre `.env.example` e `Settings`

O sistema MUST validar consistência entre campos obrigatórios definidos em
`src/config/settings.py` e variáveis documentadas em `.env.example`.

#### Scenario: Campo obrigatório ausente no `.env.example`

- **WHEN** existir campo obrigatório em `Settings` sem variável correspondente
  no `.env.example`
- **THEN** a validação MUST falhar com erro bloqueante

#### Scenario: Variável excedente no `.env.example`

- **WHEN** existir variável no `.env.example` que não corresponde a campo em
  `Settings`
- **THEN** a validação MUST reportar warning não bloqueante

### Requirement: Detecção de stale SPECs

O sistema SHALL validar frescor de SPECs em `docs/SDD/SPEC_*/SPEC.md` com
janela configurável de idade máxima e severidade por status.

#### Scenario: SPEC em rascunho acima da idade máxima

- **WHEN** uma SPEC com status de rascunho exceder a idade máxima configurada
- **THEN** a validação MUST falhar com erro bloqueante

#### Scenario: SPEC concluída acima da idade máxima

- **WHEN** uma SPEC concluída exceder a idade máxima configurada
- **THEN** a validação MUST reportar warning sem bloquear o workflow

### Requirement: Validação de fronteiras arquiteturais por imports

O sistema MUST impedir dependências entre camadas fora das regras permitidas de
import em `src/`, por análise estática.

#### Scenario: Violação de camada detectada

- **WHEN** um arquivo importar módulo de camada não permitida pela matriz de
  regras
- **THEN** a validação MUST falhar com erro bloqueante indicando origem e
  destino da violação

### Requirement: Verificação de segredos no diff

O sistema MUST executar scanner de segredos no diff do pull request como gate
de segurança complementar.

#### Scenario: Segredo detectado no delta do PR

- **WHEN** o scanner identificar potencial segredo no diff analisado
- **THEN** o workflow MUST falhar com erro bloqueante e registrar evidência
  mínima para investigação

### Requirement: Contrato de saída e severidade padronizados

O sistema SHALL padronizar saída dos validadores com classificação explícita em
`ERROR` e `WARNING`, preservando previsibilidade para triagem.

#### Scenario: Múltiplas violações em um mesmo run

- **WHEN** os validadores encontrarem combinações de warnings e erros
- **THEN** o resultado final MUST falhar somente se houver pelo menos um
  `ERROR`, mantendo warnings reportados no output
