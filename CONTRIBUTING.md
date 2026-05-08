# Contribuindo com o Binance Phicube

Obrigado por se interessar em contribuir com o **Binance Phicube**! 🎉

Este documento descreve as diretrizes para contribuir com o projeto de forma organizada e eficiente. Antes de começar, leia também o nosso [MANIFESTO.md](./MANIFESTO.md) para entender os princípios que guiam o projeto.

---

## 📋 Código de Conduta

Ao participar deste projeto, você concorda em respeitar o nosso [Código de Conduta](./CODE_OF_CONDUCT.md). Comportamentos desrespeitosos não serão tolerados.

---

## 🐛 Reportando Bugs

Se encontrou um bug, abra uma **Issue** no GitHub com as seguintes informações:

1. **Título claro** descrevendo o problema.
2. **Passos para reproduzir** o bug.
3. **Comportamento esperado** vs. **comportamento atual**.
4. **Ambiente**: sistema operacional, versão do Python, etc.
5. **Logs ou mensagens de erro** relevantes (nunca inclua credenciais ou chaves de API).

---

## 💡 Sugerindo Funcionalidades

Para sugerir uma nova funcionalidade:

1. Verifique se já existe uma Issue similar aberta.
2. Abra uma nova Issue com o label `enhancement`.
3. Descreva o problema que a funcionalidade resolve e como ela se alinha ao [MANIFESTO.md](./MANIFESTO.md).

---

## 🔧 Contribuindo com Código

### Fluxo Obrigatório (MCP Serena)

Toda contribuição de feature, bugfix relevante ou mudança arquitetural deve seguir o fluxo:

```text
SPEC -> Planner Agent -> Task Graph -> Dev Agent (com Serena) -> Validation Agent -> Commit / Review Gate
```

Referência oficial do fluxo: `docs/SDD/MCP_SERENA_FLOW.md`.

Regras objetivas:

- Sem SPEC aprovada, não inicia implementação.
- Sem Task Graph aprovado, não inicia codificação.
- Sem parecer aprovado do Validation Agent, não libera commit/merge.

### Uso disciplinado do Codex (obrigatório)

Para reduzir retrabalho e respostas vagas, todo pedido ao Codex deve seguir:

- `Goal`: o que mudar.
- `Context`: arquivos/logs/erros relevantes.
- `Constraints`: regras e limites.
- `Done when`: evidências de conclusão.

Template oficial: `docs/CODEX_TASK_TEMPLATE.md`.

Referências operacionais:

- `AGENTS.md` (regras duráveis para agentes)
- `PLANS.md` (planejamento de tarefas complexas)
- `code_review.md` (checklist de revisão)

Puxão de orelha (anti-padrões que atrasam o time):

- Pedido genérico sem erro reproduzível e sem arquivos-alvo.
- Mudança grande sem planejamento explícito.
- Prompt com regras permanentes que deveriam estar em `AGENTS.md`.
- Pedido de automação antes do fluxo manual estar estável.

Protocolo de criticidade (obrigatorio):

- Se o pedido vier sem `Goal/Context/Constraints/Done when`, interromper e reescrever o pedido no template antes de executar.
- Se houver mudanca ampla sem plano, abrir `PLANS.md` (ou usar `/plan`) antes de qualquer alteracao de codigo.
- Se a regra for recorrente, registrar no `AGENTS.md` e parar de repetir no prompt.
- Se a acao pedir mais permissao que o necessario, reduzir escopo e justificar tecnicamente.

Regras para criar/editar skills no projeto:

- Uma skill deve resolver um fluxo unico e repetitivo.
- `description` deve ser curta e conter gatilho claro de invocacao (`Use when ...`).
- Comecar com `SKILL.md` instrucional; adicionar `scripts/` apenas quando houver ganho claro de determinismo.
- Validar habilidade de trigger implicito/explicito antes de considerar a skill pronta.

### 1. Fork e Clone

```bash
# Faça um fork do repositório no GitHub e clone o seu fork
git clone https://github.com/<seu-usuario>/binance-phicube.git
cd binance-phicube
```

### 2. Crie uma Branch

Use nomes descritivos para suas branches:

```bash
git checkout -b feat/nome-da-funcionalidade
# ou
git checkout -b fix/descricao-do-bug
# ou
git checkout -b docs/atualizacao-de-documentacao
```

### 3. Faça suas Alterações

- Mantenha o código limpo e legível.
- Siga as convenções de estilo já existentes no projeto.
- **Nunca commite chaves de API, senhas ou qualquer credencial**.
- Adicione ou atualize testes para as funcionalidades que você alterar.

### 4. Commit com Mensagens Claras

Use mensagens de commit descritivas (em português ou inglês):

```text
feat: adiciona monitoramento de múltiplos símbolos
fix: corrige cálculo do stop loss no Futures
docs: atualiza instruções de instalação no README
```

### 5. Abra um Pull Request

- Faça push da sua branch para o seu fork.
- Abra um Pull Request (PR) para a branch `main` deste repositório.
- Descreva claramente o que foi feito e referencie a Issue relacionada (ex.: `Closes #42`).
- Aguarde a revisão dos mantenedores.

---

## 🔒 Segurança

Se você descobrir uma vulnerabilidade de segurança, **não abra uma Issue pública**. Entre em contato diretamente com os mantenedores do projeto.

---

## 📌 Boas Práticas

- Toda contribuição deve estar alinhada aos princípios do [MANIFESTO.md](./MANIFESTO.md).
- Prefira pequenos PRs focados a grandes PRs com múltiplas mudanças.
- Documente o que você faz — código bem documentado facilita a manutenção.

---

Agradecemos sua contribuição! Juntos tornamos o **Binance Phicube** mais robusto e confiável. 🚀
