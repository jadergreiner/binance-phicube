## ADDED Requirements

### Requirement: Canonical OpenSpec CLI
O repositório MUST adotar o CLI oficial `openspec` como único fluxo canônico para criação, exploração, aplicação e arquivamento de mudanças.

#### Scenario: Team member starts a new change
- **WHEN** um membro do time iniciar uma nova mudança
- **THEN** ele MUST usar comandos do `openspec` oficial e artefatos em `openspec/changes/<change-name>/`

### Requirement: Deprecated local compatibility workflow
O repositório MUST descontinuar o fluxo compat local (`tools/openspec_local.py`) como caminho recomendado de operação.

#### Scenario: Contributor follows repository documentation
- **WHEN** um contribuidor consultar README e guias operacionais
- **THEN** a documentação MUST apontar apenas para o fluxo oficial `openspec` e indicar depreciação do compat local

### Requirement: Transition policy for in-flight local changes
Mudanças iniciadas no fluxo compat local MUST ter política de transição explícita antes de avançar para implementação.

#### Scenario: Existing local change needs implementation
- **WHEN** existir uma mudança ativa iniciada no fluxo local compat
- **THEN** o time MUST migrar ou reconciliar os artefatos para o fluxo oficial antes de executar `openspec apply`
