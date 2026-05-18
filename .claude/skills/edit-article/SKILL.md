---
name: edit-article
description: Revisa e melhora artigos com foco em clareza, estrutura, fluidez e consistência de tom, preservando intenção original.
reference:
  - https://github.com/mattpocock/skills/tree/main/skills/personal/edit-article
tools:
  - Read
  - Bash
activation_hints:
  - "use edit-article"
  - "editar artigo"
  - "revisar texto"
  - "melhorar escrita"
  - "polir artigo"
---

# Skill: Edit Article

## Mission

Elevar a qualidade editorial de um artigo sem distorcer a ideia central, com
melhor organização, linguagem precisa e leitura fluida.

## When to use

- Texto está correto, mas confuso, prolixo ou inconsistente.
- Artigo precisa de revisão para publicação interna/externa.
- É necessário adaptar tom e legibilidade para um público-alvo.

## Inputs mínimos

- Texto original completo.
- Público-alvo e objetivo do artigo.
- Tom desejado (formal, didático, técnico, executivo).
- Restrições editoriais (tamanho, termos obrigatórios, idioma).

## Execution protocol

1. **Intent capture**

- Identificar mensagem principal e objetivo do texto.
- Confirmar público-alvo e contexto de uso.

1. **Structure pass**

- Reorganizar fluxo lógico do conteúdo:
  - abertura/contexto
  - desenvolvimento
  - conclusão/ação
- Eliminar redundâncias e blocos fora de ordem.

1. **Clarity pass**

- Simplificar frases longas e ambíguas.
- Substituir termos vagos por linguagem específica.
- Manter precisão técnica quando necessário.

1. **Tone and consistency pass**

- Uniformizar tom e nível de formalidade.
- Padronizar terminologia e estilo entre seções.

1. **Conciseness pass**

- Remover excesso sem perder conteúdo essencial.
- Melhorar densidade informativa por parágrafo.

1. **Final quality check**

- Validar legibilidade, coerência e aderência ao objetivo.
- Garantir que a intenção original foi preservada.

1. **Human gate**

- Entregar versão revisada com principais mudanças resumidas.
- Aplicar ajustes finais conforme feedback humano.

## Davi governance gates

- Não alterar fatos técnicos sem evidência/contexto.
- Em conteúdo sensível (legal/financeiro/médico), sinalizar limites.
- Pedir revisão especializada quando aplicável.
- Preservar autoria e intenção original do texto.

## Output obrigatório

- Status: `revised` | `blocked`
- Versão revisada do artigo
- Resumo das mudanças principais
- Pontos que exigem validação humana
- Próximo passo recomendado (publicar ou revisar)

## Quality rules

- Clareza e precisão acima de ornamentação.
- Evitar reescrita que mude significado.
- Melhorias devem ser rastreáveis e justificáveis.
- Tom final deve ser adequado ao público definido.
