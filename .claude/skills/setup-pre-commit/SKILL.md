---
name: setup-pre-commit
description: Configura e valida hooks de pre-commit para padronizar qualidade local antes de commit/push.
reference:
  - https://github.com/mattpocock/skills/tree/main/skills/misc/setup-pre-commit
tools:
  - Read
  - Bash
activation_hints:
  - "use setup-pre-commit"
  - "configurar pre-commit"
  - "ativar hooks"
  - "pre-commit setup"
  - "lint antes de commit"
---

# Skill: Setup Pre-commit

## Mission

Padronizar validações locais de qualidade com hooks de pre-commit para reduzir
falhas tardias em CI e manter baseline consistente de código.

## When to use

- Projeto ainda não tem hooks locais padronizados.
- Time quer bloquear commits com lint/test críticos falhando.
- Repositório está com recorrência de erro evitável em revisão/CI.

## Inputs mínimos

- Stack e linters/testes relevantes do projeto.
- Regras mínimas obrigatórias por commit.
- Política de severidade (bloqueante vs aviso).
- Ambiente alvo (Windows/Linux/macOS) quando necessário.

## Execution protocol

1. **Baseline check**

- Verificar se já existe configuração de pre-commit.
- Mapear comandos de qualidade já adotados no projeto.

1. **Hook policy definition**

- Definir checks por estágio:
  - formatação
  - lint
  - testes rápidos
  - validações de segurança (quando aplicável)
- Classificar quais checks são bloqueantes.

1. **Setup configuration**

- Criar/atualizar arquivo de configuração de hooks.
- Manter comandos curtos e reprodutíveis.

1. **Install hooks**

- Instalar e ativar hooks no repositório local.
- Garantir instruções de bootstrap para novos contribuidores.

1. **Run validation**

- Executar hooks manualmente para validar setup.
- Corrigir falhas de configuração antes de concluir.

1. **Human gate**

- Submeter política final (bloqueios, escopo e trade-offs) ao humano.
- Ajustar rigor conforme decisão formal.

1. **Closeout**

- Documentar uso operacional dos hooks.
- Registrar como desativar temporariamente em emergência (com governança).

## Davi governance gates

- Hook bloqueante novo exige aprovação humana quando impacta fluxo do time.
- Não incluir checks longos/determinísticos ruins no pre-commit padrão.
- Mudanças em política de qualidade devem ser rastreáveis.

## Output obrigatório

- Status: `ready` | `blocked` | `completed`
- Política de hooks definida
- Arquivos/configurações criadas/alteradas
- Resultado de validação local
- Decisões humanas registradas
- Próximos passos para rollout

## Quality rules

- Priorizar checks rápidos e determinísticos no pre-commit.
- Evitar acoplamento excessivo de ambiente local.
- Documentar claramente bootstrap e troubleshooting.
- Não usar bypass como solução padrão de fluxo.
