## Why

O repositório está operando com dois fluxos concorrentes de OpenSpec (CLI oficial e compat local), o que cria ambiguidade operacional e risco de execução inconsistente entre membros do time. Esta mudança é necessária agora para consolidar uma única fonte de verdade e reduzir retrabalho de governança.

## What Changes

- Definir o CLI `openspec` oficial (npm) como fluxo canônico para `propose`, `explore`, `apply` e `archive`.
- Descontinuar o fluxo compat local (`tools/openspec_local.py`) para uso diário.
- Atualizar documentação e comandos operacionais para remover instruções conflitantes.
- Registrar política de transição para mudanças já iniciadas no fluxo local.

## Capabilities

### New Capabilities
- `openspec-workflow-governance`: padroniza regras de uso do OpenSpec no repositório, incluindo comando canônico, política de transição e critérios de conformidade.

### Modified Capabilities
- Nenhuma.

## Impact

- Documentação: `README.md`, `AGENTS.md` (ou documento de governança equivalente).
- Ferramentas: `tools/phicube_ops_cli.py` (remoção/ajuste de comandos compat locais).
- Processo: execução de mudanças passa a exigir `openspec` oficial como entrada padrão.
