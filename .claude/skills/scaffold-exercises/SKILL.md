---
name: scaffold-exercises
description: Gera scaffolds de exercícios práticos com estrutura consistente, objetivos claros, critérios de aceite e solução separada.
reference:
  - https://github.com/mattpocock/skills/tree/main/skills/misc/scaffold-exercises
tools:
  - Read
  - Bash
activation_hints:
  - "use scaffold-exercises"
  - "criar exercícios"
  - "gerar kata"
  - "montar prática guiada"
  - "exercise scaffold"
---

# Skill: Scaffold Exercises

## Mission

Criar exercícios reproduzíveis para aprendizado/treino com progressão clara,
feedback objetivo e estrutura pronta para execução.

## When to use

- É necessário treinar equipe/agentes em um tópico técnico específico.
- Deseja criar katas/labs com níveis de dificuldade progressivos.
- Precisa de material prático com validação automática.

## Inputs mínimos

- Tema/competência alvo.
- Nível esperado (iniciante, intermediário, avançado).
- Linguagem/stack de referência.
- Critério de avaliação (testes, checklist, output esperado).

## Execution protocol

1. **Define learning outcomes**

- Especificar habilidades a serem exercitadas.
- Traduzir habilidades em resultados observáveis.

1. **Design exercise set**

- Planejar blocos de exercício com progressão:
  - básico
  - intermediário
  - avançado (quando aplicável)
- Limitar escopo de cada exercício para foco único.

1. **Scaffold structure**

- Gerar estrutura mínima por exercício:
  - enunciado
  - entradas/saídas esperadas
  - constraints
  - arquivos iniciais/stubs
  - testes/checks

1. **Prepare evaluation mechanism**

- Definir como validar conclusão:
  - testes automatizados
  - critérios binários
  - rubric de qualidade (se necessário)

1. **Author solutions and hints**

- Disponibilizar solução de referência separada do enunciado.
- Incluir dicas graduais para desbloqueio.

1. **Human gate**

- Submeter pacote de exercícios para validação humana.
- Ajustar dificuldade/escopo conforme feedback.

1. **Closeout**

- Entregar kit final pronto para uso.
- Incluir instruções de execução e avaliação.

## Davi governance gates

- Exercícios não devem contradizer regras RN/RA/RG do projeto.
- Conteúdo de avaliação deve ser verificável, não subjetivo.
- Sem critério de sucesso explícito, exercício permanece `draft`.

## Output obrigatório

- Status: `draft` | `ready`
- Objetivos de aprendizado
- Lista de exercícios e nível
- Estrutura/scaffold gerada
- Estratégia de avaliação
- Soluções e dicas (separadas)
- Pendências de validação humana

## Quality rules

- Cada exercício deve ter objetivo único e mensurável.
- Dificuldade deve evoluir progressivamente.
- Testes/checks devem cobrir o comportamento esperado.
- Soluções não devem vazar no enunciado principal.
