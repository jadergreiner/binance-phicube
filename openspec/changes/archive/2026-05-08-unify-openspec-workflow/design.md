## Context

Atualmente existem dois caminhos para OpenSpec no repositório: o CLI oficial (`openspec`) e um compat local (`tools/openspec_local.py`) com documentação associada. Essa duplicidade amplia risco de divergência entre artefatos, comandos e expectativa de revisão.

## Goals / Non-Goals

**Goals:**
- Estabelecer um único fluxo oficial de OpenSpec para todo o time.
- Eliminar instruções e comandos conflitantes do fluxo local compat.
- Definir transição segura para mudanças já abertas.

**Non-Goals:**
- Alterar requisitos funcionais de trading.
- Refatorar o processo SDD completo.
- Reestruturar histórico de SPECs antigas.

## Decisions

- Decisão 1: `openspec` oficial será a interface canônica de governança de mudanças.
  - Racional: já está instalado, inicializado e gera skills/commands integrados para as IDEs em uso.
  - Alternativa considerada: manter dual stack oficial + compat local.
  - Motivo de descarte: aumenta custo cognitivo e chance de execução inconsistente.

- Decisão 2: o compat local será marcado como descontinuado e removido do caminho principal.
  - Racional: evitar descoberta acidental por novos contribuidores.
  - Alternativa considerada: manter apenas como fallback silencioso.
  - Motivo de descarte: fallback não governado perpetua ambiguidade.

- Decisão 3: mudanças abertas em compat local devem migrar para estrutura oficial antes de `apply`.
  - Racional: manter rastreabilidade única no OpenSpec oficial.

## Risks / Trade-offs

- [Risco] Perda de contexto de mudanças iniciadas no fluxo local.
  -> Mitigação: checklist de migração e validação por `openspec validate`.

- [Risco] Resistência de adoção por hábito de comandos antigos.
  -> Mitigação: atualizar docs, exemplos e incluir aviso explícito de depreciação.

- [Trade-off] Remover fallback local reduz flexibilidade offline.
  -> Mitigação: documentar pré-requisito mínimo (`npm` + `openspec`) e troubleshooting.

## Migration Plan

1. Atualizar documentação para referenciar apenas `openspec` oficial.
2. Ajustar CLI operacional para não promover `openspec_local.py` como fluxo padrão.
3. Migrar mudanças locais ativas para artefatos oficiais quando necessário.
4. Executar `openspec validate --strict` nas mudanças afetadas.
5. Comunicar regra de governança em `AGENTS.md`.

## Open Questions

- O compat local será removido imediatamente ou em uma janela curta de depreciação?
- A política de migração exige script automatizado ou apenas procedimento manual?
